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
    // Lot #624 : la souris sur un repère ouvre en bas à droite la fiche de sa terre, telle que `/departs` et `/maison` l'ont
    // servie à la pose ; rien n'est relu ni calculé. Hors de tout repère, la fiche se cache.
    // Lot #613 : un clic sur un repère dépose au service le choix de sa terre (`choisir_depart`), hors du fil principal ; le
    // panneau en haut au centre dit le reçu tel que le service le rend : son tick, ou sa raison de refus. Unity ne juge rien.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class ReperesDeDepart : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "terres de départ incomplètes";
        public const float PERIODE_RELECTURE_S = 2f, HAUTEUR_REPERE = 2f, DIAMETRE_REPERE_KM = 40f;
        public static readonly Color COULEUR_REPERE = Color.white; // saturation nulle et valeur pleine : aucune cellule ne la prend
        private const float EPAISSEUR_REPERE_KM = 0.1f, ECART_PLAN = 0.2f, MARGE = 16f, TAILLE_CARACTERE = 25f, LARGEUR_FICHE = 380f; private const int TAILLE_NOM = 16, TAILLE_POLICE = 24, RETRAIT = 14;
        private static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0); private static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        private static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.78f); // celui de FicheDeCellule
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        private CarteDessinee carte; private ClientDeparts departs; private ClientMaison maisons;
        private Task<(Lecture<DepartsLus> departs, List<(FicheDeDepart fiche, Lecture<MaisonLue> maison)> maisons)> enCours;
        private double prochaineLecture; private bool complet; // toutes les fiches posées : plus aucune lecture ne part
        private ClientIntention intentions; private Task<RecuIntention> depot; // le choix déposé, relevé par Pas
        private Transform racine; private Material materiau; private Text texte, texteFiche, texteChoix; private GameObject panneau, panneauChoix;
        private readonly HashSet<long> poses = new HashSet<long>(); private readonly List<Object> crees = new List<Object>();
        private readonly List<(FicheDeDepart fiche, MaisonLue maison, long tick, Vector3 centre)> terres = new List<(FicheDeDepart, MaisonLue, long, Vector3)>();

        public int ReperesPoses => poses.Count;
        public string TexteAffiche => texte != null && texte.gameObject.activeSelf ? texte.text : null;
        public FicheDeDepart Survolee { get; private set; }
        public string FicheAffichee => panneau != null && panneau.activeSelf ? texteFiche.text : null;
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        public bool ChoixEnVol => depot != null; // jusqu'au pas qui relève le reçu
        public RecuIntention RecuDuChoix { get; private set; }
        public FicheDeDepart TerreDuChoix { get; private set; }
        public string ChoixAffiche => panneauChoix != null && panneauChoix.activeSelf ? texteChoix.text : null;
        private void Start() => Demarrer();
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();
        public void Demarrer() {
            carte = GetComponent<CarteDessinee>();
            if (carte.camera == null) { Debug.LogError("ReperesDeDepart : la carte n'a pas de caméra, les absences ne s'afficheraient pas", this); return; }
            Construire(); departs = new ClientDeparts(port, ClientDeparts.DelaiMinimal); maisons = new ClientMaison(port, ClientDeparts.DelaiMinimal);
            intentions = new ClientIntention(port, ClientDeparts.DelaiMinimal);
        }
        public void Arreter() {
            departs?.Dispose(); maisons?.Dispose(); intentions?.Dispose(); departs = null; maisons = null; intentions = null; enCours = null; depot = null;
            foreach (Object o in crees) Detruire(o);
            crees.Clear(); poses.Clear(); terres.Clear(); racine = null; materiau = null; texte = texteFiche = texteChoix = null; panneau = panneauChoix = null; Survolee = null;
            RecuDuChoix = null; TerreDuChoix = null;
        }
        // Le clic : la terre sous l'écran, s'il y en a une et qu'aucun choix n'est en vol, est déposée au service hors du fil principal.
        public void Choisir(Vector2 ecran) {
            Survoler(ecran); FicheDeDepart terre = Survolee;
            if (terre == null || intentions == null || depot != null) return;
            ClientIntention client = intentions; string corps = "{\"type\":\"choisir_depart\",\"seigneurie\":" + Entier(terre.Id) + "}";
            TerreDuChoix = terre; RecuDuChoix = null; depot = Task.Run(() => client.Deposer(corps)); AfficherChoix();
        }
        // Le reçu dit tel quel : le tick qu'il nomme (jamais +1), la raison du refus ou la cause de l'absence, mot pour mot.
        public static string DireLeChoix(FicheDeDepart fiche, RecuIntention recu) =>
            recu == null ? "Choix envoyé au monde : " + fiche.Nom
            : recu.Acceptee ? "Terre choisie : " + fiche.Nom + "\nLe monde l'applique au tick suivant (après le tick " + Entier(recu.AppliqueeAuTick.Value) + ")."
            : recu.Presente ? "Choix refusé pour " + fiche.Nom + " :\n" + recu.Erreur
            : "Choix sans réponse pour " + fiche.Nom + " :\n" + recu.Absence;
        private void AfficherChoix() { if (panneauChoix == null) return; texteChoix.text = DireLeChoix(TerreDuChoix, RecuDuChoix); panneauChoix.SetActive(true); }
        // Le point de l'écran sous la souris, posé sur le plan des repères.
        public void Survoler(Vector2 ecran) {
            if (carte == null || carte.camera == null) return;
            Ray rayon = carte.camera.ScreenPointToRay(ecran);
            if (new Plane(transform.up, transform.TransformPoint(0, HAUTEUR_REPERE, 0)).Raycast(rayon, out float distance)) SurvolerPoint(rayon.GetPoint(distance)); else Quitter();
        }
        // La terre dont le disque contient le point (distance horizontale au centre ≤ rayon), la plus proche s'il y en a plusieurs.
        public void SurvolerPoint(Vector3 monde) {
            Vector3 ici = transform.InverseTransformPoint(monde); float meilleure = DIAMETRE_REPERE_KM / 2; int trouvee = -1;
            for (int i = 0; i < terres.Count; i++) { float d = new Vector2(ici.x - terres[i].centre.x, ici.z - terres[i].centre.z).magnitude; if (d <= meilleure) { meilleure = d; trouvee = i; } }
            Survolee = trouvee < 0 ? null : terres[trouvee].fiche; AfficherFiche(trouvee);
        }
        public void Quitter() { Survolee = null; AfficherFiche(-1); }
        public static string Decrire(FicheDeDepart fiche, long tick, MaisonLue maison) {
            var s = new StringBuilder(fiche.Nom).Append("\nMaison : ").Append(fiche.Maison).Append("\nSiège : ").Append(fiche.Siege.Nom).Append(", cellule ").Append(Entier(fiche.CellId));
            s.Append("\nHabitants de la cellule : ").Append(Entier(fiche.Habitants)).Append(" au tick ").Append(Entier(tick));
            s.Append("\nSuzerain : ").Append(fiche.Suzerain != null ? fiche.Suzerain.Nom : "aucun, le monde n'en nomme pas").Append(fiche.Voisins.Count == 0 ? "\nVoisins : aucun" : "\nVoisins :");
            foreach (VoisinDeDepart v in fiche.Voisins) s.Append("\n  cellule ").Append(Entier(v.CellId)).Append(", ").Append(v.Puissance != null ? v.Puissance.Nom : "aucune puissance nommée").Append(", ").Append(Entier(v.Habitants)).Append(" habitants");
            return s.Append("\nLieux tenus : ").Append(Entier(maison.Lieux.Count)).ToString();
        }
        private static string Entier(long v) => v.ToString(CultureInfo.InvariantCulture);
        private void AfficherFiche(int i) {
            if (panneau == null) return;
            panneau.SetActive(i >= 0); if (i >= 0) texteFiche.text = Decrire(terres[i].fiche, terres[i].tick, terres[i].maison);
        }
        public void Pas(double maintenant) {
            if (departs == null) return;
            if (depot != null && depot.IsCompleted) {
                RecuDuChoix = depot.IsFaulted ? RecuIntention.Absente("intention : " + depot.Exception.GetBaseException().Message) : depot.Result; depot = null; AfficherChoix();
            }
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
                else if (maison.Donnees.Siege.Position is PointCarte siege) Poser(fiche, maison.Donnees, lues.Donnees.Tick, siege);
                else manques.Append('\n').Append(fiche.Nom).Append(" : siège hors carte, ").Append(maison.Donnees.Absents["siege"]);
            }
            complet = manques.Length == 0;
            if (complet) Dire(""); else { Dire(MESSAGE_ABSENCE + manques); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
        }
        // Un disque plat sur le siège, le nom de la terre un peu au nord, lisible d'en haut comme les villes.
        private void Poser(FicheDeDepart fiche, MaisonLue maison, long tick, PointCarte siege) {
            if (materiau == null) { materiau = new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial) { name = "Repère", color = COULEUR_REPERE }; crees.Add(materiau); } // la carte n'est posée qu'avec ce matériau
            if (racine == null) { racine = new GameObject("Repères des terres de départ").transform; racine.SetParent(transform, false); crees.Add(racine.gameObject); }
            var repere = new GameObject("Repère " + fiche.Nom).transform; repere.SetParent(racine, false); repere.localPosition = carte.PositionSurLaCarte(siege, HAUTEUR_REPERE).Value;
            GameObject disque = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disque.name = "Disque"; Detruire(disque.GetComponent<Collider>()); disque.GetComponent<MeshRenderer>().sharedMaterial = materiau;
            disque.transform.SetParent(repere, false); disque.transform.localScale = new Vector3(DIAMETRE_REPERE_KM, EPAISSEUR_REPERE_KM / 2, DIAMETRE_REPERE_KM); // le cylindre primitif : 1 de large, 2 de haut
            Font police = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); var nom = new GameObject("Nom").AddComponent<TextMesh>();
            nom.transform.SetParent(repere, false); nom.transform.SetLocalPositionAndRotation(new Vector3(0, 0, DIAMETRE_REPERE_KM / 2), VERS_LE_BAS);
            nom.font = police; nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
            nom.fontSize = TAILLE_NOM; nom.characterSize = TAILLE_CARACTERE; nom.anchor = TextAnchor.LowerCenter; nom.color = Color.black; nom.text = fiche.Nom;
            poses.Add(fiche.Id); terres.Add((fiche, maison, tick, repere.localPosition));
        }
        // En haut à gauche de l'écran, sur la caméra de la carte ; caché tant que rien ne manque. La fiche de la terre survolée
        // en bas à droite : le bas à gauche est à la fiche de cellule, le haut à droite à l'horloge. Le choix de la terre en haut
        // au centre, caché tant qu'aucun choix n'est envoyé.
        private void Construire() {
            var toile = new GameObject("Toile des repères", typeof(RectTransform)); toile.transform.SetParent(transform, false); crees.Add(toile);
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = carte.camera;
            canvas.planeDistance = carte.camera.nearClipPlane + ECART_PLAN; canvas.sortingOrder = 1;
            var echelle = toile.AddComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = RESOLUTION_REFERENCE;
            texte = new GameObject("Absences", typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(toile.transform, false);
            var cadre = (RectTransform)texte.transform; cadre.anchorMin = cadre.anchorMax = cadre.pivot = Vector2.up; cadre.anchoredPosition = new Vector2(MARGE, -MARGE);
            texte.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); texte.fontSize = TAILLE_POLICE; texte.color = Color.white; texte.raycastTarget = false;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow; texte.verticalOverflow = VerticalWrapMode.Overflow; Dire("");
            panneau = new GameObject("Fiche de la terre", typeof(RectTransform)); panneau.transform.SetParent(toile.transform, false);
            var fond = panneau.AddComponent<Image>(); fond.color = FOND; fond.raycastTarget = false;
            var coin = (RectTransform)panneau.transform; coin.anchorMin = coin.anchorMax = coin.pivot = Vector2.right; coin.anchoredPosition = new Vector2(-MARGE, MARGE);
            var pile = panneau.AddComponent<VerticalLayoutGroup>(); pile.padding = new RectOffset(RETRAIT, RETRAIT, RETRAIT, RETRAIT); pile.childControlWidth = pile.childControlHeight = true;
            var ajuste = panneau.AddComponent<ContentSizeFitter>(); ajuste.horizontalFit = ajuste.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            texteFiche = new GameObject("Texte", typeof(RectTransform)).AddComponent<Text>(); texteFiche.transform.SetParent(panneau.transform, false);
            texteFiche.font = texte.font; texteFiche.fontSize = TAILLE_POLICE; texteFiche.color = Color.white; texteFiche.raycastTarget = false;
            texteFiche.horizontalOverflow = HorizontalWrapMode.Overflow; texteFiche.verticalOverflow = VerticalWrapMode.Overflow; panneau.SetActive(false);
            // Le panneau du choix : la même fiche, ancrée en haut au centre.
            panneauChoix = Object.Instantiate(panneau, toile.transform, false); panneauChoix.name = "Choix de la terre"; texteChoix = panneauChoix.GetComponentInChildren<Text>(true);
            var haut = (RectTransform)panneauChoix.transform; haut.anchorMin = haut.anchorMax = haut.pivot = new Vector2(0.5f, 1); haut.anchoredPosition = new Vector2(0, -MARGE);
            // Dépliée, la fiche couvre la Morée, le Kosovo et Giannitsa : elle reste dans la colonne de droite, sous l'horloge.
            texteFiche.horizontalOverflow = HorizontalWrapMode.Wrap; texteFiche.gameObject.AddComponent<LayoutElement>().preferredWidth = LARGEUR_FICHE;
        }
        private void Dire(string message) { if (texte == null) return; texte.text = message; texte.gameObject.SetActive(message != ""); }
        private static void Detruire(Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
