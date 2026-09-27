using UnityEngine;

namespace Victoria.CityMode
{
    /// <summary>
    /// Lightweight original ambience used while authored, licensed audio is not
    /// available. It produces filtered highland wind and rare distant bird calls
    /// without shipping an external recording.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    public sealed class ProceduralAmbience : MonoBehaviour
    {
        const int ClipSeconds = 2;
        AudioSource source;
        AudioClip clip;
        uint randomState = 140001u;
        float windMemory;
        double gustPhase;
        double birdPhase;
        int birdSamplesRemaining;
        int birdSamplesUntilNext;
        int sampleRate;

        void Awake()
        {
            sampleRate = Mathf.Max(22050, AudioSettings.outputSampleRate);
            source = GetComponent<AudioSource>();
            source.playOnAwake = false;
            source.loop = true;
            source.spatialBlend = 0f;
            source.volume = 0.24f;
            source.priority = 192;
            source.ignoreListenerPause = false;
            birdSamplesUntilNext = sampleRate * 5;
            clip = AudioClip.Create("Procedural highland ambience", sampleRate * ClipSeconds, 1, sampleRate, true, FillAudio);
            source.clip = clip;
            source.Play();
        }

        void FillAudio(float[] samples)
        {
            if (sampleRate <= 0)
                return;
            for (var i = 0; i < samples.Length; i++)
            {
                randomState = randomState * 1664525u + 1013904223u;
                var white = ((randomState >> 8) / 16777215f) * 2f - 1f;
                windMemory = windMemory * 0.992f + white * 0.008f;
                gustPhase += 0.37 / sampleRate;
                if (gustPhase > 1.0) gustPhase -= 1.0;
                var gust = 0.38f + 0.62f * Mathf.Pow(0.5f + 0.5f * Mathf.Sin((float)gustPhase * Mathf.PI * 2f), 2.2f);
                var output = windMemory * gust * 0.34f + white * 0.006f;

                if (birdSamplesRemaining > 0)
                {
                    var progress = 1f - birdSamplesRemaining / (sampleRate * 0.42f);
                    var envelope = Mathf.Sin(Mathf.Clamp01(progress) * Mathf.PI);
                    var frequency = Mathf.Lerp(1180f, 1720f, Mathf.Clamp01(progress));
                    birdPhase += frequency / sampleRate;
                    output += Mathf.Sin((float)(birdPhase * Mathf.PI * 2.0)) * envelope * 0.055f;
                    birdSamplesRemaining--;
                }
                else if (--birdSamplesUntilNext <= 0)
                {
                    birdSamplesRemaining = Mathf.RoundToInt(sampleRate * 0.42f);
                    birdSamplesUntilNext = sampleRate * (11 + (int)(randomState % 13u));
                    birdPhase = 0.0;
                }

                samples[i] = Mathf.Clamp(output, -0.42f, 0.42f);
            }
        }

        void OnDestroy()
        {
            if (clip != null)
                Destroy(clip);
        }
    }
}
