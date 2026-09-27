using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Effets visuels uniquement. Aucun état du monde historique n'est calculé ici.
    public sealed class AlpineEnvironment : MonoBehaviour
    {
        public string village, culture, typologie;
        public int seed, year;
        public Light sun;
        public Material sky;
        public Camera view;
        public ParticleSystem rain, snow;
        public ParticleSystem[] smoke;
        public Transform[] wheels;
        public string[] scenes, labels;
        [Range(6,23)] public float hour = 16.3f;
        [Range(0,4)] public int weather;
        public bool cycle;
        public bool showPanel = true;
        float wet, cover;
        bool ownsSky;
        readonly string[] weatherNames = { "Éclaircies", "Couvert", "Brume", "Pluie", "Neige" };

        void OnEnable()
        {
            if(Application.isPlaying && sky && !ownsSky) { sky=new Material(sky);ownsSky=true; }
            Apply(true);
        }
        void OnDestroy() { if(ownsSky && sky) Destroy(sky); }
        void Update()
        {
            if (Keyboard.current != null && Keyboard.current.hKey.wasPressedThisFrame) showPanel = !showPanel;
            if (cycle) { hour += Time.deltaTime * .07f; if (hour > 23) hour = 6; }
            foreach (var wheel in wheels) if (wheel) wheel.Rotate(Vector3.right, -24 * Time.deltaTime, Space.Self);
            Apply(false);
        }

        public void SetWeather(int state, float atHour)
        {
            weather = Mathf.Clamp(state, 0, 4); hour = atHour; Apply(true);
        }

        public void Apply(bool instant)
        {
            if (!sun || !view) return;
            float daylight = Mathf.Clamp01(Mathf.Sin((hour - 6) / 12 * Mathf.PI));
            float cloudy = weather == 0 ? 0 : weather == 2 ? .45f : .86f;
            float wind = weather == 3 ? 2.4f : weather == 4 ? 1.8f : .9f;
            wet = instant ? (weather == 3 ? 1 : 0) : Mathf.MoveTowards(wet, weather == 3 ? 1 : 0, Time.deltaTime * .15f);
            cover = instant ? (weather == 4 ? 1 : 0) : Mathf.MoveTowards(cover, weather == 4 ? 1 : 0, Time.deltaTime * .1f);
            Shader.SetGlobalFloat("_AlpineWind", wind);
            Shader.SetGlobalFloat("_AlpineWet", wet);
            Shader.SetGlobalFloat("_AlpineSnow", cover);
            Shader.SetGlobalFloat("_AlpineNight", Mathf.SmoothStep(0, 1, Mathf.Clamp01((.45f - daylight) * 3.5f)) + cloudy * .15f);
            Shader.SetGlobalColor("_AlpineAmbient",Color.Lerp(new Color(.055f,.078f,.13f),new Color(.25f,.28f,.32f),Mathf.Sqrt(daylight)) * (1-cloudy*.15f));
            Shader.SetGlobalFloat("_AlpineDaylight",Mathf.Sqrt(daylight));
            sun.transform.rotation = Quaternion.Euler((hour - 6) / 12 * 180, -40, 0);
            sun.intensity = Mathf.Lerp(.12f, 1.9f, Mathf.SmoothStep(0,1,Mathf.Clamp01(daylight/.24f))) * (1 - cloudy * .67f);
            sun.color = Color.Lerp(new Color(1,.60f,.31f), new Color(1,.93f,.80f), Mathf.Clamp01(daylight * 1.7f));
            if (weather != 0) sun.color = Color.Lerp(sun.color,new Color(.76f,.83f,.94f),cloudy);
            if (daylight<.03f) { sun.transform.rotation=Quaternion.Euler(38,145,0);sun.color=new Color(.45f,.59f,1);sun.intensity=.26f; }
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = Color.Lerp(new Color(.025f,.043f,.085f),new Color(.46f,.56f,.68f),daylight) * (1 - cloudy * .22f);
            RenderSettings.ambientEquatorColor = Color.Lerp(new Color(.018f,.025f,.046f),new Color(.34f,.37f,.32f),daylight);
            RenderSettings.ambientGroundColor = Color.Lerp(new Color(.009f,.012f,.02f),new Color(.15f,.18f,.13f),daylight);
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogStartDistance = weather == 2 ? 80 : 180;
            RenderSettings.fogEndDistance = weather == 2 ? 490 : weather == 3 ? 670 : weather == 4 ? 620 : 1150;
            RenderSettings.fogColor = Color.Lerp(new Color(.035f,.05f,.085f),weather == 0 ? new Color(.43f,.54f,.62f) : new Color(.53f,.59f,.62f),daylight);
            if (sky)
            {
                sky.SetFloat("_Exposure", Mathf.Lerp(.15f,1.05f,daylight));
                sky.SetColor("_SkyTint",Color.Lerp(new Color(.45f,.50f,.56f),new Color(.55f,.57f,.59f),cloudy));
                sky.SetFloat("_AtmosphereThickness",1.0f + cloudy * .65f);
                RenderSettings.skybox = sky;
            }
            view.backgroundColor = RenderSettings.fogColor;
            SetEmission(rain, weather == 3 ? 1700 : 0);
            SetEmission(snow, weather == 4 ? 950 : 0);
            foreach (var system in smoke)
                if (system) { var noise = system.noise; noise.strength = .18f * wind; }
        }

        static void SetEmission(ParticleSystem system, float rate)
        {
            if (!system) return;
            var emission = system.emission; emission.rateOverTime = rate;
            if (!system.isPlaying) system.Play();
        }

        void OnGUI()
        {
            if (!showPanel) return;
            GUI.color = new Color(.055f,.085f,.073f,.94f);
            GUI.DrawTexture(new Rect(22,22,340,288),Texture2D.whiteTexture);
            GUI.color = new Color(.94f,.91f,.82f);
            GUI.Label(new Rect(40,34,300,22),"FORGE  /  VILLAGE ALPIN",new GUIStyle(GUI.skin.label){fontSize=12});
            GUI.Label(new Rect(38,60,312,38),village,new GUIStyle(GUI.skin.label){fontSize=25,fontStyle=FontStyle.Bold});
            GUI.Label(new Rect(40,100,300,25),year+" · "+culture,new GUIStyle(GUI.skin.label){fontSize=13});
            GUI.Label(new Rect(40,128,300,24),"Lumière  "+Mathf.FloorToInt(hour).ToString("00")+":"+Mathf.FloorToInt(hour%1*60).ToString("00"));
            hour = GUI.HorizontalSlider(new Rect(40,159,298,20),hour,6,23);
            for (int i=0;i<weatherNames.Length;i++)
                if (GUI.Toggle(new Rect(39+(i%3)*102,185+(i/3)*29,102,25),weather==i,weatherNames[i],"Button")) weather=i;
            cycle = GUI.Toggle(new Rect(40,254,270,23),cycle,"Faire défiler la journée");
            for (int i=0;i<labels.Length;i++)
                if (GUI.Button(new Rect(22+i*183,324,176,30),"F"+(i+1)+" · "+labels[i])) SceneManager.LoadScene(scenes[i]);
            GUI.Label(new Rect(25,Screen.height-34,Screen.width-45,28),"Flèches : déplacer   ·   Molette : zoom   ·   Clic droit : tourner   ·   F : vue générale   ·   H : masquer les commandes",new GUIStyle(GUI.skin.label){fontSize=13});
        }
    }
}
