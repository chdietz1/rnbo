#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "StageRegistry.h"

EarStageProcessor::EarStageProcessor()
    : AudioProcessor (BusesProperties()
                          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "EarStage", createLayout())
{
    azimuth   = apvts.getRawParameterValue (kAzimuth);
    elevation = apvts.getRawParameterValue (kElevation);
    distance  = apvts.getRawParameterValue (kDistance);
    width     = apvts.getRawParameterValue (kWidth);
    room      = apvts.getRawParameterValue (kRoom);
    roomSize  = apvts.getRawParameterValue (kRoomSize);
    headSize  = apvts.getRawParameterValue (kHeadSize);
    gain      = apvts.getRawParameterValue (kGain);

    instanceNumber = StageRegistry::get().add (this);
}

EarStageProcessor::~EarStageProcessor()
{
    StageRegistry::get().remove (this);
}

juce::AudioProcessorValueTreeState::ParameterLayout EarStageProcessor::createLayout()
{
    using namespace juce;
    std::vector<std::unique_ptr<RangedAudioParameter>> params;

    auto degrees = AudioParameterFloatAttributes().withLabel (juce::String::fromUTF8 ("\xc2\xb0"))
                       .withStringFromValueFunction ([] (float v, int) { return String (juce::roundToInt (v)); });

    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kAzimuth, 1 }, "Azimut",
                                                             NormalisableRange<float> (-180.0f, 180.0f, 0.1f), 0.0f, degrees));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kElevation, 1 }, "Elevation",
                                                             NormalisableRange<float> (-40.0f, 90.0f, 0.1f), 0.0f, degrees));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kDistance, 1 }, "Distanz",
                                                             NormalisableRange<float> (0.5f, 15.0f, 0.01f, 0.4f), 1.5f,
                                                             AudioParameterFloatAttributes().withLabel ("m")
                                                                 .withStringFromValueFunction ([] (float v, int) { return String (v, 2); })));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kWidth, 1 }, "Breite",
                                                             NormalisableRange<float> (0.0f, 120.0f, 0.1f), 30.0f, degrees));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kRoom, 1 }, "Raum",
                                                             NormalisableRange<float> (0.0f, 100.0f, 0.1f), 25.0f,
                                                             AudioParameterFloatAttributes().withLabel ("%")));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kRoomSize, 1 }, "Raumgroesse",
                                                             NormalisableRange<float> (0.0f, 100.0f, 0.1f), 40.0f,
                                                             AudioParameterFloatAttributes().withLabel ("%")));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kHeadSize, 1 }, "Kopfradius",
                                                             NormalisableRange<float> (7.0f, 10.5f, 0.01f), 8.75f,
                                                             AudioParameterFloatAttributes().withLabel ("cm")));
    params.push_back (std::make_unique<AudioParameterFloat> (ParameterID { kGain, 1 }, "Gain",
                                                             NormalisableRange<float> (-24.0f, 12.0f, 0.1f), 0.0f,
                                                             AudioParameterFloatAttributes().withLabel ("dB")));
    return { params.begin(), params.end() };
}

bool EarStageProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto in  = layouts.getMainInputChannelSet();
    const auto out = layouts.getMainOutputChannelSet();
    return out == juce::AudioChannelSet::stereo()
        && (in == juce::AudioChannelSet::mono() || in == juce::AudioChannelSet::stereo());
}

void EarStageProcessor::prepareToPlay (double sampleRate, int)
{
    engine.prepare (sampleRate);
}

void EarStageProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;

    earstage::Params p;
    p.azimuthDeg   = azimuth->load();
    p.elevationDeg = elevation->load();
    p.distanceM    = distance->load();
    p.widthDeg     = width->load();
    p.roomAmount   = room->load() * 0.01f;
    p.roomSize     = roomSize->load() * 0.01f;
    p.headRadiusM  = headSize->load() * 0.01f;
    p.gainDb       = gain->load();
    engine.setParams (p);

    const int numIn = getTotalNumInputChannels();
    const int n = buffer.getNumSamples();
    if (numIn == 0 || buffer.getNumChannels() < 2)
    {
        buffer.clear();
        return;
    }

    // In-place ist sicher: die Engine liest Sample i, bevor sie Sample i schreibt.
    engine.process (buffer.getReadPointer (0),
                    numIn > 1 ? buffer.getReadPointer (1) : nullptr,
                    buffer.getWritePointer (0), buffer.getWritePointer (1), n);
}

void EarStageProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    state.setProperty ("customName", getCustomName(), nullptr);
    if (auto xml = state.createXml())
        copyXmlToBinary (*xml, destData);
}

void EarStageProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (auto xml = getXmlFromBinary (data, sizeInBytes))
    {
        auto tree = juce::ValueTree::fromXml (*xml);
        if (tree.hasType (apvts.state.getType()))
        {
            setCustomName (tree.getProperty ("customName").toString());
            tree.removeProperty ("customName", nullptr);
            apvts.replaceState (tree);
        }
    }
}

void EarStageProcessor::updateTrackProperties (const TrackProperties& properties)
{
    const juce::ScopedLock sl (nameLock);
    trackName = properties.name;
    trackColour = properties.colour;
}

juce::String EarStageProcessor::getDisplayName() const
{
    const juce::ScopedLock sl (nameLock);
    if (customName.isNotEmpty()) return customName;
    if (trackName.isNotEmpty())  return trackName;
    return "Kanal " + juce::String (instanceNumber);
}

juce::Colour EarStageProcessor::getTrackColour() const
{
    const juce::ScopedLock sl (nameLock);
    return trackColour;
}

void EarStageProcessor::setCustomName (const juce::String& name)
{
    const juce::ScopedLock sl (nameLock);
    customName = name.trim();
}

juce::String EarStageProcessor::getCustomName() const
{
    const juce::ScopedLock sl (nameLock);
    return customName;
}

juce::AudioProcessorEditor* EarStageProcessor::createEditor()
{
    return new EarStageEditor (*this);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new EarStageProcessor();
}
