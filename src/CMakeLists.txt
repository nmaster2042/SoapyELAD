cmake_minimum_required(VERSION 3.0)
project(SoapyELAD)

find_package(SoapySDR REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUSB REQUIRED libusb-1.0)

include_directories(${LIBUSB_INCLUDE_DIRS})

SOAPY_SDR_MODULE_UTIL(
    TARGET SoapyELAD
    SOURCES SoapyELAD.cpp
    LIBRARIES ${LIBUSB_LIBRARIES}
)
