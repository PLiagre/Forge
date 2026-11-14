using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #849 : la seconde galerie du socle. Les seize jetons, les trois matières, un feuillet de registre et les neuf états : la langue du 28 octobre, sans aucune partie chargée.
    public sealed class GalerieDuRegistre : MonoBehaviour
    {
        void Start() => Creer().transform.SetParent(transform, false);

        // Un texte de la galerie, à la hauteur de ses lignes : les zones ne se chevauchent pas par leurs cadres.
        static Text Ecrit(Transform parent, string contenu, float x, float y, float largeur, string jeton, int taille = SocleInterface.Corps)
        {
            var texte = SocleInterface.Texte(parent, contenu, x, y, largeur, taille); texte.color = SocleInterface.Couleur(jeton);
            SocleInterface.Ajuster(texte);
            return texte;
        }
        static RectTransform Zone(Transform fond, string nom, float y, float hauteur) => SocleInterface.Cadre(fond, nom, 0, y, 1920, hauteur);

        public static GameObject Creer()
        {
            var racine = new GameObject("Galerie du registre");
            var evenements = new GameObject("Navigation", typeof(EventSystem), typeof(InputSystemUIInputModule)); evenements.transform.SetParent(racine.transform);
            var toile = new GameObject("Registre", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster)); toile.transform.SetParent(racine.transform);
            toile.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
            var echelle = toile.GetComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = new Vector2(1920, 1080);
            var fond = SocleInterface.Cadre(toile.transform, "Fond", 0, 0, 1920, 1080);
            var pierre = SocleInterface.Aplat(fond, Color.white); pierre.sprite = MatieresCabinet.Pierre; pierre.type = Image.Type.Tiled;

            var titre = Zone(fond, "Zone titre", 16, 112);
            Ecrit(titre, "F O R G E", 96, 0, 900, "papier", 54); Ecrit(titre, "LE CABINET  /  LA LANGUE DU REGISTRE", 100, 78, 1100, "or-vieilli");

            var jetons = Zone(fond, "Zone jetons", 136, 140);
            for (int i = 0; i < SocleInterface.Jetons.Count; i++)
            {
                string nom = SocleInterface.Jetons[i], hex = "#" + ColorUtility.ToHtmlStringRGB(SocleInterface.Couleur(nom));
                var pastille = SocleInterface.Cadre(jetons, "Jeton " + nom, 96 + i % 8 * 218, i / 8 * 76, 204, 64); SocleInterface.Aplat(pastille, SocleInterface.Couleur("papier"));
                SocleInterface.Aplat(SocleInterface.Cadre(pastille, "Cadre", 3, 3, 58, 58), SocleInterface.Couleur("encre"));
                SocleInterface.Aplat(SocleInterface.Cadre(pastille, "Teinte", 5, 5, 54, 54), SocleInterface.Couleur(nom));
                Ecrit(pastille, nom, 70, 5, 130, "encre"); Ecrit(pastille, hex, 70, 34, 130, "secondaire", 16);
            }

            var matieres = Zone(fond, "Zone matières", 288, 108);
            string[] noms = { "pierre", "bois-brule", "metal" };
            for (int i = 0; i < noms.Length; i++)
            {
                float x = 96 + i * 324;
                Ecrit(matieres, noms[i], x, 0, 300, "papier");
                SocleInterface.Aplat(SocleInterface.Cadre(matieres, "Cadre " + noms[i], x - 2, 28, 304, 84), SocleInterface.Couleur("papier")); // la pierre sur la pierre ne se verrait pas
                var plaque = SocleInterface.Aplat(SocleInterface.Cadre(matieres, "Matière " + noms[i], x, 30, 300, 80), Color.white); plaque.sprite = MatieresCabinet.Matiere(noms[i]); plaque.type = Image.Type.Tiled;
            }

            var feuillet = SocleInterface.Cadre(fond, "Feuillet du registre", 96, 408, 920, 344); MatieresCabinet.Habiller(feuillet.gameObject.AddComponent<Image>());
            SocleInterface.Rubrique(feuillet, "Le grenier, exemple", 24, 20, 872);
            SocleInterface.LigneDeCompte(feuillet, "Exemple de compte", 1250m, "kg", 24, 88, 872);
            SocleInterface.LigneDeCompte(feuillet, "Exemple absent", null, "kg", 24, 124, 872);
            SocleInterface.PiedDeFeuillet(feuillet, "Exemple, aucun tick reçu", 24, 188, 872);
            SocleInterface.NoteEnMarge(feuillet, "Une note en marge dit la cause ; le nombre reste dans la ligne.", 24, 222, 872);
            SocleInterface.Separateur(feuillet, 24, 264, 872);
            var sceller = SocleInterface.Commande(feuillet, "Sceller l'exemple", 24, 286, null, true, "Exemple d'engagement : aucun ordre envoyé.");
            SocleInterface.Sceau(sceller.transform, 8, 8);

            var etats = Zone(fond, "Zone états", 764, 178);
            for (int i = 0; i < EtatsDuCabinet.Table.Count; i++)
            {
                float x = 48 + i * 204;
                Ecrit(etats, EtatsDuCabinet.Table[i].Nom, x, 0, 192, "papier");
                EtatsDuCabinet.Poser(etats, (EtatDuCabinet)i, "Ouvrir le grenier", x, 28, 192, 150);
            }

            var pied = Zone(fond, "Zone pied", 956, 30);
            Ecrit(pied, "Démonstration visuelle — aucune partie chargée", 96, 0, 1200, "papier");
            SocleInterface.Commande(fond, "Coin de l'écran", 1580, 1036, null, true, "Une infobulle au coin reste entière dans l'écran.");
            return racine;
        }

#if UNITY_EDITOR
        [UnityEditor.MenuItem("Forge/Interface/Galerie du registre")]
        public static void OuvrirGalerie()
        {
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            var galerie = new GameObject("Scène du registre", typeof(GalerieDuRegistre));
            var camera = new GameObject("Caméra de galerie").AddComponent<Camera>();
            camera.transform.SetParent(galerie.transform);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = SocleInterface.Couleur("pierre");
            UnityEditor.EditorApplication.ExecuteMenuItem("Window/General/Game");
            UnityEditor.EditorApplication.isPlaying = true;
        }
#endif
    }
}
