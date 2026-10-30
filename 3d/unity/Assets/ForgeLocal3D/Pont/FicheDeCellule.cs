using System;
using System.Globalization;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont {
    // Lot #526 : le joueur survole une cellule et lit sa fiche. Puissance, maison et villes viennent de la carte servie
    // (`/carte`, déjà lue par CarteDessinee) ; habitants, faim et dette viennent de `/monde`, relu toutes les
    // `PERIODE_LECTURE_S` hors du fil principal, avec la maison du joueur, nulle tant qu'elle n'est pas servie.
    // Lot #929 : la fiche écrit le nom servi du bourg (`NomsDesTerres`, rang 0 de `/lieu`) et la date du monde, plus le tick ni l'identifiant ;
    // le nom arrive après le survol, « Bourg en lecture » d'abord, et `Pas` réécrit la fiche quand il change.
    // Rien n'est calculé ici : une puissance ou une maison que le monde ne nomme pas se déclare, une faim non calculée (-1) aussi, un monde absent aussi.
    // Le survol vient de `SurvolDeCarte` (la souris) ou d'une épreuve ; hors de toute cellule, la fiche se cache.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class FicheDeCellule : MonoBehaviour {
        public const float PERIODE_LECTURE_S = 0.5f;
        private static readonly TimeSpan DELAI = TimeSpan.FromSeconds(2);
        private static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        private static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.78f);
        private const float ECART_PLAN = 0.2f, MARGE = 16f; private const int RETRAIT = 14, TAILLE_POLICE = 24;

        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;

        private CarteDessinee carte; private ClientMonde client; private Task<Lecture<MondeAvecMaisonLu>> enCours; private double prochaineLecture;
        private Lecture<MondeAvecMaisonLu> monde; private NomsDesTerres noms; private double dernierPas;
        private GameObject toile, fond; private Text texte;

        public CelluleDeCarte Survolee { get; private set; }
        public MondeLu MondeLu => monde != null && monde.Presente ? monde.Donnees.Monde : null;
        public string MaisonDuJoueur => monde != null && monde.Presente ? monde.Donnees.MaisonDuJoueur : null; // null : pas servie, ou réponse absente
        public string AbsenceDuMonde => monde != null && !monde.Presente ? monde.Absence : null; // null tant que rien n'est lu
        public string TexteAffiche => texte != null && fond.activeSelf ? texte.text : null;
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        public string NomDuBourg { get; private set; } // le nom passé à la dernière écriture

        private void Start() => Demarrer();
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();

        public void Demarrer() {
            carte = GetComponent<CarteDessinee>();
            if (carte.camera == null) { Debug.LogError("FicheDeCellule : la carte n'a pas de caméra, la fiche ne s'affiche pas", this); return; }
            Construire(); client = new ClientMonde(port, DELAI); noms = NomsDesTerres.Local(port);
        }

        public void Arreter() { client?.Dispose(); client = null; enCours = null; noms = null; if (toile != null) { if (Application.isPlaying) Destroy(toile); else DestroyImmediate(toile); } toile = null; }

        public void Pas(double maintenant) {
            if (client == null) return;
            dernierPas = maintenant;
            if (enCours != null && enCours.IsCompleted) { monde = enCours.Result; enCours = null; Afficher(); }
            if (Survolee != null && noms != null && Bourg(maintenant) != NomDuBourg) Afficher(); // le nom est arrivé, ou a échoué
            if (enCours != null || maintenant < prochaineLecture) return;
            prochaineLecture = maintenant + PERIODE_LECTURE_S;
            ClientMonde c = client; enCours = Task.Run(() => c.LireAvecMaison());
        }

        // Le point de l'écran sous la souris : la cellule sous lui, sur le plan de la carte.
        public void Survoler(Vector2 ecran) {
            if (carte == null || carte.camera == null) return;
            Ray rayon = carte.camera.ScreenPointToRay(ecran);
            if (new Plane(transform.up, transform.position).Raycast(rayon, out float distance)) SurvolerPoint(rayon.GetPoint(distance));
            else Quitter();
        }

        public void SurvolerPoint(Vector3 monde) { Survolee = carte != null ? carte.CelluleSous(monde) : null; Afficher(); }
        public void Quitter() { Survolee = null; Afficher(); }

        public static string Decrire(CelluleDeCarte c, Lecture<MondeLu> monde) {
            var s = new StringBuilder("Cellule ").Append(Entier(c.CellId));
            if (c.Villes.Count > 0) { s.Append(" · "); for (int i = 0; i < c.Villes.Count; i++) s.Append(i > 0 ? ", " : "").Append(c.Villes[i].Nom); }
            s.Append("\nPuissance : ").Append(c.Puissance != null ? c.Puissance.Nom : "aucune, le monde n'en nomme pas");
            s.Append("\nMaison : ").Append(c.Maison != null ? c.Maison.Nom : "aucune, le monde n'en nomme pas");
            if (monde == null) return s.Append("\nHabitants et faim : en attente du monde").ToString();
            if (!monde.Presente) return s.Append("\nHabitants et faim : ").Append(CarteDessinee.MESSAGE_ABSENCE).Append(" (").Append(monde.Absence).Append(')').ToString();
            MondeLu m = monde.Donnees; CelluleDuMonde vivante = null;
            foreach (CelluleDuMonde x in m.Cellules) if (x.CellId == c.CellId) { vivante = x; break; }
            if (vivante == null) return s.Append("\nHabitants et faim : cellule absente du monde servi au tick ").Append(Entier(m.Tick)).ToString();
            s.Append("\nHabitants : ").Append(Entier(vivante.Population)).Append(" au tick ").Append(Entier(m.Tick));
            s.Append("\nFaim : ").Append(vivante.HungerTicks < 0 ? "non calculée" : Entier(vivante.HungerTicks) + " ticks de manque");
            s.Append("\nDette de nourriture : ").Append(vivante.FoodDeficitKg < 0 ? "non calculée" : vivante.FoodDeficitKg.ToString("R", CultureInfo.InvariantCulture) + " kg");
            return s.ToString();
        }

        // Lot #910 — la même terre écrite en noms : le bourg déjà lu (`NomsDesTerres`, rang 0), la date servie, des jours et des masses.
        // Ni identifiant ni tick, même dans une absence ; une faim ou une dette à -1 reste « non calculée », 0 est une mesure. Rien n'est lu ici.
        public static string Decrire(CelluleDeCarte c, Lecture<MondeLu> monde, string nomDuBourg) {
            string id = Entier(c.CellId);
            string titre = nomDuBourg == null || nomDuBourg == NomsDesTerres.NomEnLecture ? "Bourg en lecture" : TexteDuMonde.Absence(nomDuBourg, id);
            var s = new StringBuilder(titre); bool premiere = true;
            foreach (VilleDeCarte v in c.Villes) {
                if (titre == nomDuBourg && v.Nom == nomDuBourg) continue; // la ville qui porte le nom du bourg n'est pas répétée
                s.Append(premiere ? " · " : ", ").Append(v.Nom); premiere = false;
            }
            s.Append("\nPuissance : ").Append(c.Puissance != null ? c.Puissance.Nom : "aucune, le monde n'en nomme pas");
            s.Append("\nMaison : ").Append(c.Maison != null ? c.Maison.Nom : "aucune, le monde n'en nomme pas");
            if (monde == null) return s.Append("\nHabitants et faim : en attente du monde").ToString();
            if (!monde.Presente) return s.Append("\nHabitants et faim : ").Append(TexteDuMonde.Absence(monde.Absence, id)).ToString();
            MondeLu m = monde.Donnees; CelluleDuMonde vivante = null;
            foreach (CelluleDuMonde x in m.Cellules) if (x.CellId == c.CellId) { vivante = x; break; }
            if (vivante == null) return s.Append("\nHabitants et faim : absente du monde servi").ToString();
            s.Append("\nHabitants : ").Append(TexteDuMonde.Nombre(vivante.Population)).Append(vivante.Population == 0 || vivante.Population == 1 ? " habitant" : " habitants")
                .Append(" · ").Append(TexteDuMonde.Date(m.Date));
            s.Append("\nFaim : ").Append(vivante.HungerTicks < 0 ? "non calculée" : TexteDuMonde.Jours(vivante.HungerTicks) + " de manque");
            s.Append("\nDette de nourriture : ").Append(vivante.FoodDeficitKg < 0 ? "non calculée" : TexteDuMonde.Masse(vivante.FoodDeficitKg));
            return s.ToString();
        }

        private void Afficher() {
            if (fond == null) return;
            fond.SetActive(Survolee != null);
            if (Survolee == null || noms == null) return;
            NomDuBourg = Bourg(dernierPas);
            texte.text = Decrire(Survolee, VersMonde(monde), NomDuBourg);
        }

        // Le nom servi, ou ce qui l'empêche : « nom en cours de lecture » avant qu'il arrive, la cause après un échec.
        private string Bourg(double maintenant) => noms.Bourg(Survolee.CellId, maintenant) ?? noms.Raison(Survolee.CellId, 0);

        private static Lecture<MondeLu> VersMonde(Lecture<MondeAvecMaisonLu> lu) => lu == null ? null : lu.Presente ? Lecture<MondeLu>.De(lu.Donnees.Monde) : Lecture<MondeLu>.Absent(lu.Absence);
        private static string Entier(long v) => v.ToString(CultureInfo.InvariantCulture);

        // En bas à gauche de l'écran, sur la caméra de la carte.
        private void Construire() {
            toile = new GameObject("Toile de la fiche", typeof(RectTransform)); toile.transform.SetParent(transform, false);
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = carte.camera;
            canvas.planeDistance = carte.camera.nearClipPlane + ECART_PLAN; canvas.sortingOrder = 1;
            var echelle = toile.AddComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = RESOLUTION_REFERENCE;
            fond = new GameObject("Fiche", typeof(RectTransform)); fond.transform.SetParent(toile.transform, false);
            fond.AddComponent<Image>().color = FOND; fond.GetComponent<Image>().raycastTarget = false;
            var cadre = (RectTransform)fond.transform; cadre.anchorMin = cadre.anchorMax = cadre.pivot = Vector2.zero; cadre.anchoredPosition = new Vector2(MARGE, MARGE);
            var pile = fond.AddComponent<VerticalLayoutGroup>(); pile.padding = new RectOffset(RETRAIT, RETRAIT, RETRAIT, RETRAIT); pile.childControlWidth = pile.childControlHeight = true;
            var ajuste = fond.AddComponent<ContentSizeFitter>(); ajuste.horizontalFit = ajuste.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            texte = new GameObject("Texte", typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(fond.transform, false);
            texte.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); texte.fontSize = TAILLE_POLICE; texte.color = Color.white; texte.raycastTarget = false;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow; texte.verticalOverflow = VerticalWrapMode.Overflow;
            fond.SetActive(false);
        }
    }
}
