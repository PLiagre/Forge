using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace Forge.Pont {
    // Lot #689 : de la carte à la capitale. Le composant relit l'aiguillage toutes les `PERIODE_LECTURE_S` ; quand le joueur
    // confirme une terre qui a un kit, il charge sa scène, une seule fois, et ne lit plus rien. Une terre sans kit le dit
    // dans un panneau. La ville ne s'ouvre que sur une confirmation vue : une lecture `Depart`, puis une lecture `Ville` ;
    // une terre déjà confirmée à l'ouverture laisse le joueur sur la carte. Une absence n'arme, ne montre ni ne cache rien.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    public sealed class PassageALaCapitale : MonoBehaviour {
        public const float PERIODE_LECTURE_S = 1;
        public const string MESSAGE_SANS_KIT = "Pas encore de kit pour cette terre";
        private static readonly TimeSpan DELAI = TimeSpan.FromSeconds(5);
        private static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.78f);
        // En haut à droite de la vue de la carte, sous le bandeau du cabinet et à droite de ses feuillets.
        private static readonly Vector2 POSITION = new Vector2(-24, -124), TAILLE = new Vector2(474, 112);
        private const float ECART_PLAN = 0.2f; private const int RETRAIT = 16, TAILLE_POLICE = 26;

        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera; // vide : celle de la CarteDessinee du même objet
        public Action<string> ChargerScene { get; set; } = nom => SceneManager.LoadScene(nom);

        private Task<Lecture<CapitaleAOuvrir>> enCours; private double prochaineLecture; private bool departVu;
        private GameObject toile; private Text texte;

        public bool RequeteEnVol => enCours != null && !enCours.IsCompleted;
        public string Absence { get; private set; } // la cause de la dernière lecture manquée ; null après une lecture servie
        public bool PanneauVisible => toile != null && toile.activeSelf;
        public string TexteAffiche => PanneauVisible ? texte.text : null;
        public string SceneDemandee { get; private set; } // null tant que rien n'est chargé

        private void Start() { var carte = GetComponent<CarteDessinee>(); Demarrer(camera != null ? camera : carte != null ? carte.camera : null); }
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();

        public void Demarrer(Camera vue) {
            camera = vue;
            if (camera == null) { Debug.LogError("PassageALaCapitale : pas de caméra, le passage ne lit rien", this); return; }
            Construire();
        }

        public void Arreter() { enCours = null; if (toile != null) Detruire(toile); toile = null; }

        public void Pas(double maintenant) {
            if (toile == null || SceneDemandee != null) return;
            if (enCours != null && enCours.IsCompleted) { var fini = enCours; enCours = null; Appliquer(fini); }
            if (enCours != null || SceneDemandee != null || maintenant < prochaineLecture) return;
            prochaineLecture = maintenant + PERIODE_LECTURE_S;
            int p = port; enCours = Task.Run(() => AiguillageDeCapitale.Lire(p, DELAI));
        }

        private void Appliquer(Task<Lecture<CapitaleAOuvrir>> fini) {
            if (fini.IsFaulted) { Absence = "passage : " + fini.Exception.GetBaseException().Message; return; }
            var lecture = fini.Result;
            if (!lecture.Presente) { Absence = lecture.Absence; return; }
            Absence = null;
            var capitale = lecture.Donnees;
            toile.SetActive(capitale.Destination == DestinationDeCapitale.PasDeKit);
            if (capitale.Destination == DestinationDeCapitale.Depart) departVu = true;
            else if (capitale.Destination == DestinationDeCapitale.Ville && departVu) { SceneDemandee = capitale.Scene; (sceneRemise, celluleRemise) = (capitale.Scene, capitale.Cellule); ChargerScene(capitale.Scene); }
        }

        // Une toile sans parent : CabinetDeCarte cache toutes celles de l'objet de la carte, pas celle-ci.
        private void Construire() {
            toile = new GameObject("Toile du passage à la capitale", typeof(RectTransform));
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera;
            canvas.planeDistance = camera.nearClipPlane + ECART_PLAN; canvas.sortingOrder = 1;
            var echelle = toile.AddComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = new Vector2(1920, 1080); echelle.matchWidthOrHeight = 0;
            var fond = new GameObject("Pas de kit", typeof(RectTransform)); fond.transform.SetParent(toile.transform, false);
            fond.AddComponent<Image>().color = FOND;
            var cadre = (RectTransform)fond.transform; cadre.anchorMin = cadre.anchorMax = cadre.pivot = Vector2.one;
            cadre.anchoredPosition = POSITION; cadre.sizeDelta = TAILLE;
            texte = new GameObject("Message", typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(fond.transform, false);
            var zone = texte.rectTransform; zone.anchorMin = Vector2.zero; zone.anchorMax = Vector2.one; zone.offsetMin = new Vector2(RETRAIT, RETRAIT); zone.offsetMax = new Vector2(-RETRAIT, -RETRAIT);
            texte.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); texte.fontSize = TAILLE_POLICE; texte.color = Color.white; texte.raycastTarget = false;
            texte.alignment = TextAnchor.MiddleLeft; texte.horizontalOverflow = HorizontalWrapMode.Wrap; texte.verticalOverflow = VerticalWrapMode.Truncate;
            texte.text = MESSAGE_SANS_KIT;
            toile.SetActive(false);
        }

        // Lot #701 : la cellule du siège, lue dans /maison par l'aiguillage, retenue juste avant le chargement pour la
        // seule scène demandée. Une prise l'efface, que la scène corresponde ou non : une seule ville en profite.
        private static string sceneRemise; private static long? celluleRemise;
        public static long? PrendreCelluleRemise(string scene)
        {
            long? cellule = scene == sceneRemise ? celluleRemise : null;
            (sceneRemise, celluleRemise) = (null, null);
            return cellule;
        }

        private static void Detruire(UnityEngine.Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }

        // Lot #690 : à l'ouverture de la carte, le passage manquant se pose sur chaque CarteDessinee, avec son port.
        // Un second avis ne crée rien. Une autre scène n'est pas touchée. Le Start prend ensuite la caméra.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Installer() {
            SceneManager.sceneLoaded -= AuChargement; SceneManager.sceneLoaded += AuChargement;
            AuChargement(SceneManager.GetActiveScene(), LoadSceneMode.Single);
        }

        public static void AuChargement(Scene scene, LoadSceneMode mode) {
            if (!scene.IsValid() || scene.name != OuvertureDeLaCarte.SCENE) return;
            foreach (CarteDessinee carte in UnityEngine.Object.FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None)) {
                if (carte.gameObject.scene != scene || carte.GetComponent<PassageALaCapitale>() != null) continue;
                carte.gameObject.AddComponent<PassageALaCapitale>().port = carte.port;
            }
        }
    }
}
