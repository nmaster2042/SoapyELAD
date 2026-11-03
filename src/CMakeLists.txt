cmake_minimum_required(VERSION 3.0)
project(SoapyELAD VERSION 0.1.0 LANGUAGES CXX C)

find_package(SoapySDR REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUSB REQUIRED libusb-1.0)

include_directories(${LIBUSB_INCLUDE_DIRS})

SOAPY_SDR_MODULE_UTIL(
    TARGET SoapyELAD
    SOURCES SoapyELAD.cpp
    LIBRARIES ${LIBUSB_LIBRARIES}
)

# ==============================================================================
# make uninstall
# ==============================================================================
if(NOT TARGET uninstall)
    configure_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in"
        "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
        IMMEDIATE @ONLY)

    add_custom_target(uninstall
        COMMAND ${CMAKE_COMMAND} -P "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake")
endif()
