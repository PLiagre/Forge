using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class GalerieEtats : MonoBehaviour
    {
        void Start() => Creer().transform.SetParent(transform, false);

        public static GameObject Creer()
        {
            var racine = new GameObject("Galerie des états", typeof(Canvas), typeof(CanvasScaler));
            racine.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
            var echelle = racine.GetComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = new Vector2(1920, 1080);
            var fond = new GameObject("Fond", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            fond.SetParent(racine.transform, false);
            fond.anchorMin = fond.anchorMax = fond.pivot = new Vector2(0, 1);
            fond.sizeDelta = new Vector2(1920, 1080);
            fond.GetComponent<Image>().color = SocleInterface.Couleur("fond");
            SocleInterface.Texte(fond, "F O R G E", 96, 70, 900, 54).color = SocleInterface.Couleur("papier");
            SocleInterface.Texte(fond, "LE CABINET  /  ÉTATS DE LECTURE", 100, 152, 1100).color = SocleInterface.Couleur("or");
            Carte(fond, "Consulter un dossier", 96, 242, EtatLecture.Attente,
                "La lecture demandée est en cours.");
            Carte(fond, "Lire une quantité", 984, 242, EtatLecture.Absence,
                "La source ne fournit pas cette donnée.");
            Carte(fond, "Déposer une intention", 96, 540, EtatLecture.Refus,
                "La source a refusé la demande : motif de démonstration.");
            Carte(fond, "Joindre le monde", 984, 540, EtatLecture.Panne,
                "La source est injoignable : exemple de panne.");
            SocleInterface.Texte(fond, "Chaque état nomme ce qui manque ou empêche la lecture.", 96, 844, 1600, 24).color = SocleInterface.Couleur("papier");
            SocleInterface.Texte(fond, "Démonstration visuelle — aucune partie chargée", 96, 924, 1500).color = SocleInterface.Couleur("papier");
            SocleInterface.Texte(fond, "UI-02  ·  Police Unity provisoire  ·  Motifs illustratifs, aucun ordre envoyé", 96, 966, 1600).color = SocleInterface.Couleur("or");
            return racine;
        }

        static void Carte(Transform parent, string titre, float x, float y, EtatLecture etat, string cause)
        {
            var panneau = SocleInterface.Panneau(parent, titre, x, y, 840, 250);
            var lecture = SocleInterface.Texte(panneau, "État de lecture", 24, 100, 792, 24);
            EtatsLecture.Afficher(lecture, etat, cause);
        }

#if UNITY_EDITOR
        [UnityEditor.MenuItem("Forge/Interface/Galerie des états")]
        public static void OuvrirGalerie()
        {
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            var galerie = new GameObject("Scène des états", typeof(GalerieEtats));
            var camera = new GameObject("Caméra de galerie").AddComponent<Camera>();
            camera.transform.SetParent(galerie.transform);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = SocleInterface.Couleur("fond");
            UnityEditor.EditorApplication.ExecuteMenuItem("Window/General/Game");
            UnityEditor.EditorApplication.isPlaying = true;
        }
#endif
    }
}
