using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Pont {
    // Lot #625 : un repère sur le siège de chaque terre de départ servie (`/departs`), à la place que `/maison` donne au
    // siège (`siege.point`, EPSG:3035) et que la carte convertit comme ses contours. Rien n'est deviné : une fiche absente
    // ou un siège hors carte se dit en haut à gauche, sans repère, et la lecture repart pour ce qui manque.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class ReperesDeDepart : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "terres de départ incomplètes";
        public const float PERIODE_RELECTURE_S = 2f, HAUTEUR_REPERE = 2f, DIAMETRE_REPERE_KM = 40f;
        public static readonly Color COULEUR_REPERE = Color.white; // saturation nulle et valeur pleine : aucune cellule ne la prend
        private const float EPAISSEUR_REPERE_KM = 0.1f, ECART_PLAN = 0.2f, MARGE = 16f, TAILLE_CARACTERE = 25f; private const int TAILLE_NOM = 16, TAILLE_POLICE = 24;
        private static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0); private static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        private CarteDessinee carte; private ClientDeparts departs; private ClientMaison maisons;
        private Task<(Lecture<DepartsLus> departs, List<(FicheDeDepart fiche, Lecture<MaisonLue> maison)> maisons)> enCours;
        private double prochaineLecture; private bool complet; // toutes les fiches posées : plus aucune lecture ne part
        private Transform racine; private Material materiau; private Text texte;
        private readonly HashSet<long> poses = new HashSet<long>(); private readonly List<Object> crees = new List<Object>();

        public int ReperesPoses => poses.Count;
        public string TexteAffiche => texte != null && texte.gameObject.activeSelf ? texte.text : null;
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        private void Start() => Demarrer();
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();
        public void Demarrer() {
            carte = GetComponent<CarteDessinee>();
            if (carte.camera == null) { Debug.LogError("ReperesDeDepart : la carte n'a pas de caméra, les absences ne s'afficheraient pas", this); return; }
            Construire(); departs = new ClientDeparts(port, ClientDeparts.DelaiMinimal); maisons = new ClientMaison(port, ClientDeparts.DelaiMinimal);
        }
        public void Arreter() {
            departs?.Dispose(); maisons?.Dispose(); departs = null; maisons = null; enCours = null;
            foreach (Object o in crees) Detruire(o);
            crees.Clear(); poses.Clear(); racine = null; materiau = null; texte = null;
        }
        public void Pas(double maintenant) {
            if (departs == null) return;
            if (enCours != null && enCours.IsCompleted) { var lu = enCours.Result; enCours = null; Appliquer(lu.departs, lu.maisons, maintenant); }
            if (complet || enCours != null || maintenant < prochaineLecture || carte.PositionSurLaCarte(default, 0f) == null) return;
            ClientDeparts d = departs; ClientMaison m = maisons; var deja = new HashSet<long>(poses);
            enCours = Task.Run(() => Lire(d, m, deja));
        }
        // Hors du fil principal : les terres servies, puis la fiche de chaque maison qui n'a pas encore son repère.
        private static (Lecture<DepartsLus>, List<(FicheDeDepart, Lecture<MaisonLue>)>) Lire(ClientDeparts d, ClientMaison m, HashSet<long> deja) {
            Lecture<DepartsLus> lues = d.Lire(); var fiches = new List<(FicheDeDepart, Lecture<MaisonLue>)>();
            if (lues.Presente) foreach (FicheDeDepart fiche in lues.Donnees.Fiches)
                if (!deja.Contains(fiche.Id)) fiches.Add((fiche, m.Lire("seigneurie-" + fiche.Id.ToString(CultureInfo.InvariantCulture))));
            return (lues, fiches);
        }
        private void Appliquer(Lecture<DepartsLus> lues, List<(FicheDeDepart fiche, Lecture<MaisonLue> maison)> fiches, double maintenant) {
            var manques = new StringBuilder();
            if (!lues.Presente) manques.Append('\n').Append(lues.Absence);
            else foreach (var (fiche, maison) in fiches) {
                if (!maison.Presente) manques.Append('\n').Append(fiche.Nom).Append(" : ").Append(maison.Absence);
                else if (maison.Donnees.Siege.Position is PointCarte siege) Poser(fiche, siege);
                else manques.Append('\n').Append(fiche.Nom).Append(" : siège hors carte, ").Append(maison.Donnees.Absents["siege"]);
            }
            complet = manques.Length == 0;
            if (complet) Dire(""); else { Dire(MESSAGE_ABSENCE + manques); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
        }
        // Un disque plat sur le siège, le nom de la terre un peu au nord, lisible d'en haut comme les villes.
        private void Poser(FicheDeDepart fiche, PointCarte siege) {
            if (materiau == null) { materiau = new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial) { name = "Repère", color = COULEUR_REPERE }; crees.Add(materiau); } // la carte n'est posée qu'avec ce matériau
            if (racine == null) { racine = new GameObject("Repères des terres de départ").transform; racine.SetParent(transform, false); crees.Add(racine.gameObject); }
            var repere = new GameObject("Repère " + fiche.Nom).transform; repere.SetParent(racine, false); repere.localPosition = carte.PositionSurLaCarte(siege, HAUTEUR_REPERE).Value;
            GameObject disque = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disque.name = "Disque"; Detruire(disque.GetComponent<Collider>()); disque.GetComponent<MeshRenderer>().sharedMaterial = materiau;
            disque.transform.SetParent(repere, false); disque.transform.localScale = new Vector3(DIAMETRE_REPERE_KM, EPAISSEUR_REPERE_KM / 2, DIAMETRE_REPERE_KM); // le cylindre primitif : 1 de large, 2 de haut
            Font police = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); var nom = new GameObject("Nom").AddComponent<TextMesh>();
            nom.transform.SetParent(repere, false); nom.transform.SetLocalPositionAndRotation(new Vector3(0, 0, DIAMETRE_REPERE_KM / 2), VERS_LE_BAS);
            nom.font = police; nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
            nom.fontSize = TAILLE_NOM; nom.characterSize = TAILLE_CARACTERE; nom.anchor = TextAnchor.LowerCenter; nom.color = Color.black; nom.text = fiche.Nom;
            poses.Add(fiche.Id);
        }
        // En haut à gauche de l'écran, sur la caméra de la carte ; caché tant que rien ne manque.
        private void Construire() {
            var toile = new GameObject("Toile des repères", typeof(RectTransform)); toile.transform.SetParent(transform, false); crees.Add(toile);
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = carte.camera;
            canvas.planeDistance = carte.camera.nearClipPlane + ECART_PLAN; canvas.sortingOrder = 1;
            var echelle = toile.AddComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = RESOLUTION_REFERENCE;
            texte = new GameObject("Absences", typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(toile.transform, false);
            var cadre = (RectTransform)texte.transform; cadre.anchorMin = cadre.anchorMax = cadre.pivot = Vector2.up; cadre.anchoredPosition = new Vector2(MARGE, -MARGE);
            texte.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); texte.fontSize = TAILLE_POLICE; texte.color = Color.white; texte.raycastTarget = false;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow; texte.verticalOverflow = VerticalWrapMode.Overflow; Dire("");
        }
        private void Dire(string message) { if (texte == null) return; texte.text = message; texte.gameObject.SetActive(message != ""); }
        private static void Detruire(Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
