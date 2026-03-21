#include <SoapySDR/Device.hpp>
#include <SoapySDR/Registry.hpp>
#include <SoapySDR/Logger.hpp>
#include <libusb-1.0/libusb.h>
#include <cstring>
#include <cmath>
#include <stdexcept>
#include <vector>
#include <string>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <unistd.h>

#define ELAD_VID      0x1721
#define ELAD_S2_PID   0x061c
#define S_RATE        122880000.0
#define EP_IN         0x86
#define NUM_BUFFERS   15
#define BUFFER_SIZE   262144

class SoapyELAD : public SoapySDR::Device
{
public:
    SoapyELAD(const SoapySDR::Kwargs &) :
        _dev(nullptr), _ctx(nullptr),
        _frequency(100e6), _sampleRate(6144000),
        _running(false), _currentSpeed(0),
        _bufHead(0), _bufTail(0), _bufCount(0)
    {
        libusb_init(&_ctx);
        _openDevice();
        _buffers.resize(NUM_BUFFERS);
        for (auto &b : _buffers) b.resize(BUFFER_SIZE);
        _transfers.resize(NUM_BUFFERS, nullptr);
        _bufFilled.resize(NUM_BUFFERS, 0);
        SoapySDR_log(SOAPY_SDR_INFO, "ELAD FDM-S2 initialized");
    }

    ~SoapyELAD()
    {
        if (_running) deactivateStream(nullptr, 0, 0);
        _closeDevice();
        if (_ctx) libusb_exit(_ctx);
    }

    std::string getDriverKey() const { return "ELAD"; }
    std::string getHardwareKey() const { return "FDM-S2"; }
    size_t getNumChannels(const int dir) const { return (dir == SOAPY_SDR_RX) ? 1 : 0; }
    std::vector<std::string> getStreamFormats(const int, const size_t) const { return {"CF32"}; }
    std::string getNativeStreamFormat(const int, const size_t, double &fullScale) const {
        fullScale = 2147483648.0; return "CS32";
    }
    SoapySDR::Stream *setupStream(const int dir, const std::string &,
        const std::vector<size_t> &, const SoapySDR::Kwargs &)
    {
        if (dir != SOAPY_SDR_RX) throw std::runtime_error("Only RX supported");
        return (SoapySDR::Stream *)this;
    }
    void closeStream(SoapySDR::Stream *) { deactivateStream(nullptr, 0, 0); }

    int activateStream(SoapySDR::Stream *, const int, const long long, const size_t)
    {
        int newSpeed = _speedFromRate(_sampleRate);

        if (newSpeed != _currentSpeed) {
            _closeDevice();
            usleep(200000);
            std::string cmd = "/usr/local/bin/elad-firmware + " + std::to_string(newSpeed) + " > /dev/null 2>&1";
            system(cmd.c_str());
            sleep(1);
            _openDevice();
            _currentSpeed = newSpeed;
        }

        _setFreq(_frequency);
        _setFilter(_frequency);
        {
            std::lock_guard<std::mutex> lock(_mutex);
            _bufHead = 0; _bufTail = 0; _bufCount = 0;
            for (auto &f : _bufFilled) f = 0;
        }
        for (int i = 0; i < NUM_BUFFERS; i++) {
            _transfers[i] = libusb_alloc_transfer(0);
            libusb_fill_bulk_transfer(_transfers[i], _dev, EP_IN,
                _buffers[i].data(), BUFFER_SIZE, _staticCallback, this, 5000);
            libusb_submit_transfer(_transfers[i]);
        }
        _running = true;
        _eventThread = std::thread([this]() {
            while (_running) {
                struct timeval tv = {0, 100000};
                libusb_handle_events_timeout_completed(_ctx, &tv, nullptr);
            }
        });
        unsigned char buf[1];
        libusb_control_transfer(_dev, 0xC0, 0xE9, 0x0001, 0x0000, buf, 1, 500);
        return 0;
    }

    int deactivateStream(SoapySDR::Stream *, const int, const long long)
    {
        if (!_running) return 0;
        unsigned char buf[1];
        libusb_control_transfer(_dev, 0xC0, 0xE9, 0x0000, 0x0000, buf, 1, 500);
        _running = false;
        _cv.notify_all();
        for (auto t : _transfers) if (t) libusb_cancel_transfer(t);
        if (_eventThread.joinable()) _eventThread.join();
        for (int i = 0; i < NUM_BUFFERS; i++) {
            if (_transfers[i]) { libusb_free_transfer(_transfers[i]); _transfers[i] = nullptr; }
        }
        return 0;
    }

    int readStream(SoapySDR::Stream *, void * const *buffs,
        const size_t numElems, int &, long long &, const long timeoutUs)
    {
        if (!_running) return SOAPY_SDR_TIMEOUT;
        std::unique_lock<std::mutex> lock(_mutex);
        if (!_cv.wait_for(lock, std::chrono::microseconds(timeoutUs),
            [this]{ return _bufCount > 0 || !_running; }))
            return SOAPY_SDR_TIMEOUT;
        if (!_running) return SOAPY_SDR_TIMEOUT;
        int idx = _bufTail;
        int filled = _bufFilled[idx];
        lock.unlock();

        int bps = (_sampleRate >= 6144000) ? 2 : 4;
        size_t nSamples = std::min(numElems, (size_t)(filled / (bps * 2)));
        float *out = (float *)buffs[0];
        if (bps == 2) {
            const int16_t *in = (const int16_t *)_buffers[idx].data();
            const float scale = 1.0f / 32768.0f;
            for (size_t i = 0; i < nSamples * 2; i++) out[i] = in[i] * scale;
        } else {
            const int32_t *in = (const int32_t *)_buffers[idx].data();
            const float scale = 1.0f / 2147483648.0f;
            for (size_t i = 0; i < nSamples * 2; i++) out[i] = in[i] * scale;
        }
        {
            std::lock_guard<std::mutex> lock2(_mutex);
            _bufTail = (_bufTail + 1) % NUM_BUFFERS;
            _bufCount--;
            _bufFilled[idx] = 0;
        }
        libusb_fill_bulk_transfer(_transfers[idx], _dev, EP_IN,
            _buffers[idx].data(), BUFFER_SIZE, _staticCallback, this, 5000);
        libusb_submit_transfer(_transfers[idx]);
        return nSamples;
    }

    void setFrequency(const int, const size_t, const double freq, const SoapySDR::Kwargs &)
    { _frequency = freq; _setFreq(freq); _setFilter(freq); }

    double getFrequency(const int, const size_t) const { return _frequency; }
    SoapySDR::RangeList getFrequencyRange(const int, const size_t) const {
        return {SoapySDR::Range(100e3, 260e6)};
    }
    void setSampleRate(const int, const size_t, const double rate) { _sampleRate = rate; }
    double getSampleRate(const int, const size_t) const { return _sampleRate; }
    std::vector<double> listSampleRates(const int, const size_t) const {
        return {192000, 384000, 768000, 1536000, 3072000, 6144000};
    }

    static void _staticCallback(libusb_transfer *t)
    { ((SoapyELAD *)t->user_data)->_handleCallback(t); }

    void _handleCallback(libusb_transfer *t)
    {
        if (!_running) return;
        if (t->status == LIBUSB_TRANSFER_COMPLETED) {
            int idx = -1;
            for (int i = 0; i < NUM_BUFFERS; i++)
                if (_transfers[i] == t) { idx = i; break; }
            if (idx >= 0) {
                std::lock_guard<std::mutex> lock(_mutex);
                if (_bufCount < NUM_BUFFERS) {
                    int head = (_bufTail + _bufCount) % NUM_BUFFERS;
                    if (head == idx) {
                        _bufFilled[idx] = t->actual_length;
                        _bufCount++;
                        _cv.notify_one();
                        return;
                    }
                }
            }
        }
        if (_running) libusb_submit_transfer(t);
    }

private:
    libusb_device_handle *_dev;
    libusb_context *_ctx;
    double _frequency, _sampleRate;
    std::atomic<bool> _running;
    std::thread _eventThread;
    int _currentSpeed;
    std::vector<std::vector<uint8_t>> _buffers;
    std::vector<libusb_transfer *> _transfers;
    std::vector<int> _bufFilled;
    int _bufHead, _bufTail, _bufCount;
    std::mutex _mutex;
    std::condition_variable _cv;

    int _speedFromRate(double r) {
        if (r >= 6144000) return 6;
        if (r >= 3072000) return 5;
        if (r >= 1536000) return 4;
        if (r >= 768000)  return 3;
        if (r >= 384000)  return 2;
        return 1;
    }

    void _openDevice() {
        _dev = libusb_open_device_with_vid_pid(_ctx, ELAD_VID, ELAD_S2_PID);
        if (!_dev) throw std::runtime_error("ELAD FDM-S2 not found");
        if (libusb_kernel_driver_active(_dev, 0))
            libusb_detach_kernel_driver(_dev, 0);
        libusb_set_configuration(_dev, 1);
        libusb_claim_interface(_dev, 0);
    }

    void _closeDevice() {
        if (_dev) {
            libusb_release_interface(_dev, 0);
            libusb_close(_dev);
            _dev = nullptr;
        }
    }

    void _setFreq(double hz) {
        if (!_dev) return;
        double t = hz - floor(hz / S_RATE) * S_RATE;
        uint32_t w = (uint32_t)((4294967296.0 * t) / S_RATE);
        unsigned char buf[2] = {0, 0};
        libusb_control_transfer(_dev, 0x40, 0xF2, w&0xFFFF, (w>>16)&0xFFFF, buf, 2, 500);
    }

    void _setFilter(double freq) {
        if (!_dev) return;
        uint8_t fl;
        if (freq < 61440000) fl = 0x03;
        else if (freq < 122880000) fl = 0x02;
        else fl = 0x04;
        unsigned char buf[1];
        libusb_control_transfer(_dev, 0xC0, 0xF7, fl, 0x0002, buf, 1, 500);
    }
};

static SoapySDR::Device *makeELAD(const SoapySDR::Kwargs &args) { return new SoapyELAD(args); }

static SoapySDR::KwargsList findELAD(const SoapySDR::Kwargs &) {
    SoapySDR::KwargsList results;
    libusb_context *ctx = nullptr;
    libusb_init(&ctx);
    libusb_device_handle *dev = libusb_open_device_with_vid_pid(ctx, ELAD_VID, ELAD_S2_PID);
    if (dev) {
        SoapySDR::Kwargs info;
        info["label"] = "ELAD FDM-S2";
        info["driver"] = "ELAD";
        results.push_back(info);
        libusb_close(dev);
    }
    libusb_exit(ctx);
    return results;
}

static SoapySDR::Registry registerELAD("elad", &findELAD, &makeELAD, SOAPY_SDR_ABI_VERSION);
