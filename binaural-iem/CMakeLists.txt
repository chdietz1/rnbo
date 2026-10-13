cmake_minimum_required(VERSION 3.22)

project(EarStage VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
set(JUCE_DIR "" CACHE PATH "Optional: lokaler JUCE-Checkout (sonst wird JUCE heruntergeladen)")
if(JUCE_DIR)
    add_subdirectory(${JUCE_DIR} juce)
else()
    FetchContent_Declare(juce
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG 8.0.4
        GIT_SHALLOW TRUE)
    FetchContent_MakeAvailable(juce)
endif()

if(APPLE)
    set(EARSTAGE_FORMATS AU VST3)
else()
    set(EARSTAGE_FORMATS VST3)
endif()

juce_add_plugin(EarStage
    COMPANY_NAME "Bastelkram"
    BUNDLE_ID "ch.bastelkram.earstage"
    PLUGIN_MANUFACTURER_CODE Bstl
    PLUGIN_CODE ErSt
    FORMATS ${EARSTAGE_FORMATS}
    PRODUCT_NAME "EarStage"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE
    VST3_CATEGORIES Fx Spatial
    AU_MAIN_TYPE kAudioUnitType_Effect)

target_sources(EarStage PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp)

target_compile_definitions(EarStage PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
    JUCE_DISPLAY_SPLASH_SCREEN=0)

target_link_libraries(EarStage
    PRIVATE
        juce::juce_audio_processors
        juce::juce_gui_basics
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)

# Engine-Test (ohne JUCE)
enable_testing()
add_executable(engine_test tests/engine_test.cpp)
target_include_directories(engine_test PRIVATE Source)
add_test(NAME engine_test COMMAND engine_test)
