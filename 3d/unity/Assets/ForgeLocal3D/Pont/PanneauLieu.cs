using System;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont
{
    // Le panneau du lieu : il montre ce que le service local de `sim/` dit d'une
    // cellule, et ne calcule aucun nombre. La lecture part hors du fil principal ;
    // son résultat s'applique dans Update. Une absence remplace les nombres.
    public sealed class PanneauLieu : MonoBehaviour
    {
        public const float PERIODE_LECTURE_S = 0.25f;
        public const long CELLULE_PAR_DEFAUT = 1175;
        public const int DEFAULT_SERVICE_PORT = 8000; // celui de jeu/sim/service.py
        public const string ARGUMENT_CELLULE = "-forgeCell";
        private const string HOTE = "127.0.0.1";
        private const string NOURRITURE = "nourriture";
        private const string OUVRIERS = "ouvriers"; // les bras partis au chantier (MODELE.md, « Le chantier et ses bras »)
        private const string MARQUE_SERVICE_ABSENT = "service absent";
        private const string MARQUE_DELAI = "délai dépassé";
        private static readonly TimeSpan DELAI_LECTURE = TimeSpan.FromSeconds(2);
        private const float ECART_PLAN = 0.2f;
        private static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        private const float MARGE = 16f;
        private const int RETRAIT = 14;
        private const string POLICE = "LegacyRuntime.ttf";
        private const int TAILLE_POLICE = 24;
        private static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.78f);

        public long cellule = CELLULE_PAR_DEFAUT;
        public int port = DEFAULT_SERVICE_PORT;
        public new Camera camera;

        private Text texte;
        // Le second texte (foyers, chantier, logement), créé après le premier : `GetComponentInChildren<Text>`
        // rend toujours celui du jalon 1, que ForgeCapture écrit et que l'épreuve relit ligne par ligne.
        private Text texteFoyers;
        private ClientLieu client;
        private long celluleLue;
        private Task<LectureLieu> enCours;
        private double prochaineLecture;
        private bool dejaLu;
        private long tickAffiche;
        private string absenceAffichee;

        public string TexteAffiche => texte != null ? texte.text : null;
        public string TexteFoyers => texteFoyers != null ? texteFoyers.text : null;
        public GameObject ObjetFoyers => texteFoyers != null ? texteFoyers.gameObject : null;
        public int Reconstructions { get; private set; }
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;

        // (arguments, défaut) → cellule, ou -1 et une erreur qui nomme l'argument et la valeur reçue.
        public static long LireCellule(string[] arguments, long defaut, out string erreur)
        {
            erreur = null;
            int i = Array.IndexOf(arguments, ARGUMENT_CELLULE);
            if (i < 0) return defaut;
            if (i + 1 >= arguments.Length)
            {
                erreur = ARGUMENT_CELLULE + " sans valeur : un cell_id entier positif ou nul attendu";
                return -1;
            }
            string valeur = arguments[i + 1];
            if (long.TryParse(valeur, NumberStyles.None, CultureInfo.InvariantCulture, out long lu)) return lu;
            erreur = ARGUMENT_CELLULE + " attend un cell_id entier positif ou nul, reçu « " + valeur + " »";
            return -1;
        }

        private void Start() => Demarrer(Environment.GetCommandLineArgs());
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();

        public void Demarrer(string[] arguments)
        {
            if (camera == null)
            {
                Debug.LogError("PanneauLieu : le champ camera est vide, le panneau ne s'affiche pas", this);
                return;
            }
            Construire();
            celluleLue = LireCellule(arguments, cellule, out string erreur);
            if (erreur != null)
            {
                texte.text = erreur;
                return;
            }
            texte.text = MARQUE_SERVICE_ABSENT + " : en attente de " + Adresse();
            client = new ClientLieu(port, DELAI_LECTURE);
        }

        public void Arreter()
        {
            client?.Dispose();
            client = null;
        }

        // Ce qu'Update fait à chaque image : appliquer une lecture finie, en lancer une autre à l'heure.
        public void Pas(double maintenant)
        {
            if (enCours != null && enCours.IsCompleted)
            {
                Appliquer(enCours.Result);
                enCours = null;
            }
            if (client == null || enCours != null || maintenant < prochaineLecture) return;
            prochaineLecture = maintenant + PERIODE_LECTURE_S;
            ClientLieu lecteur = client;
            long cell = celluleLue;
            enCours = Task.Run(() => lecteur.Lire(cell));
        }

        private void Appliquer(LectureLieu lecture)
        {
            long tick = lecture.Presente ? lecture.Lieu.Tick : -1;
            if (dejaLu && tick == tickAffiche && lecture.Absence == absenceAffichee) return;
            dejaLu = true;
            tickAffiche = tick;
            absenceAffichee = lecture.Absence;
            texte.text = lecture.Presente ? Decrire(lecture.Lieu) : DireAbsence(lecture.Absence);
            // Une absence efface les chiffres d'avant : rien d'une lecture précédente ne reste à l'écran.
            texteFoyers.text = lecture.Presente ? DecrireFoyers(lecture.Lieu) : "";
            texteFoyers.gameObject.SetActive(lecture.Presente);
            Reconstructions++;
        }

        private string Adresse() => HOTE + ":" + port.ToString(CultureInfo.InvariantCulture);

        // Le client ouvre sa cause par « lieu <cell_id> : », puis la nomme. Seules ses deux
        // causes réseau (service absent, délai dépassé) disent le service absent : on les lit
        // en tête, jamais dans le reste, où un corps reçu (une 404…) peut dire n'importe quoi.
        private string DireAbsence(string cause)
        {
            string tete = "lieu " + Entier(celluleLue) + " : ";
            bool serviceAbsent = cause.StartsWith(tete + MARQUE_SERVICE_ABSENT + " sur ", StringComparison.Ordinal)
                || cause.StartsWith(tete + MARQUE_DELAI + " (", StringComparison.Ordinal);
            return serviceAbsent
                ? MARQUE_SERVICE_ABSENT + " : " + Adresse() + " — " + cause
                : "lieu illisible : " + cause;
        }

        private static string Nombre(double valeur) => valeur.ToString("R", CultureInfo.InvariantCulture);
        private static string Entier(long valeur) => valeur.ToString(CultureInfo.InvariantCulture);

        private static string Decrire(Lieu lieu)
        {
            var s = new StringBuilder();
            s.Append("Cellule ").Append(Entier(lieu.CellId)).Append(" · tick ").Append(Entier(lieu.Tick)).Append('\n');
            s.Append("Date : jour ").Append(Entier(lieu.JourDeLAnnee)).Append(" de ").Append(Entier(lieu.Annee)).Append('\n');
            s.Append("Habitants : ").Append(Entier(lieu.Population)).Append('\n');
            s.Append("Nourriture : ").Append(lieu.Stocks.TryGetValue(NOURRITURE, out double kg) ? Nombre(kg) + " kg" : "absente du panier").Append('\n');
            foreach (var marchandise in lieu.Stocks.Where(m => m.Key != NOURRITURE).OrderBy(m => m.Key, StringComparer.Ordinal))
                s.Append(marchandise.Key).Append(" : ").Append(Nombre(marchandise.Value)).Append(" kg\n");
            s.Append("Faim : ").Append(Entier(lieu.HungerTicks)).Append(" ticks de manque\n");
            s.Append("Dette de nourriture : ").Append(Nombre(lieu.FoodDeficitKg)).Append(" kg");
            return s.ToString();
        }

        // Les foyers, le chantier et le logement, lus tels quels : aucune somme, aucune division.
        private static string DecrireFoyers(Lieu lieu)
        {
            var s = new StringBuilder("Foyers par métier :");
            if (lieu.EtatFoyers == EtatFoyers.Servis && lieu.Foyers.Count == 0) s.Append(" aucun");
            else if (lieu.EtatFoyers == EtatFoyers.NonCalcules) s.Append(" non calculés par le monde");
            else if (lieu.EtatFoyers == EtatFoyers.Absents) s.Append(" absents de la réponse du service");
            else
                foreach (var metier in lieu.Foyers)
                    s.Append('\n').Append(metier.Key).Append(" : ").Append(Entier(metier.Value.Foyers)).Append(" foyers, ")
                        .Append(Entier(metier.Value.Personnes)).Append(" personnes");
            s.Append("\nAu chantier : ");
            if (lieu.EtatFoyers == EtatFoyers.NonCalcules) s.Append("non calculé");
            else if (lieu.EtatFoyers == EtatFoyers.Absents) s.Append("absent de la réponse du service");
            else if (lieu.Foyers.TryGetValue(OUVRIERS, out var ouvriers)) s.Append(Entier(ouvriers.Personnes)).Append(" bras pris aux champs");
            else s.Append("personne");
            Logement l = lieu.Logement;
            if (l == null) s.Append("\nLogement : absent du service (aucun bâtiment au plan)");
            else if (l.Loges == -1 || l.SansLogis == -1)
                s.Append("\nLogement des artisans : ").Append(Entier(l.Capacite)).Append(" places, logés et sans-logis non calculés");
            else
                s.Append("\nLogement des artisans : ").Append(Entier(l.Loges)).Append(" foyers logés, ")
                    .Append(Entier(l.SansLogis)).Append(" sans logis, ").Append(Entier(l.Capacite)).Append(" places");
            return s.ToString();
        }

        private void Construire()
        {
            var toile = new GameObject("Toile du panneau", typeof(RectTransform));
            toile.transform.SetParent(transform, false);
            var canvas = toile.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceCamera;
            canvas.worldCamera = camera;
            // Juste derrière le plan proche : rien de la scène ne passe devant le panneau.
            canvas.planeDistance = camera.nearClipPlane + ECART_PLAN;
            var echelle = toile.AddComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = RESOLUTION_REFERENCE;

            var fond = new GameObject("Fond", typeof(RectTransform));
            fond.transform.SetParent(toile.transform, false);
            var cadre = (RectTransform)fond.transform;
            cadre.anchorMin = cadre.anchorMax = cadre.pivot = new Vector2(0, 1);
            cadre.anchoredPosition = new Vector2(MARGE, -MARGE);
            fond.AddComponent<Image>().color = FOND;
            var pile = fond.AddComponent<VerticalLayoutGroup>();
            pile.padding = new RectOffset(RETRAIT, RETRAIT, RETRAIT, RETRAIT);
            pile.childControlWidth = pile.childControlHeight = true;
            var ajuste = fond.AddComponent<ContentSizeFitter>();
            ajuste.horizontalFit = ajuste.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

            pile.spacing = RETRAIT;
            texte = Ecrire(fond, "Texte");
            // Inactif et vide tant qu'aucun lieu n'est lu : la mise en page l'ignore alors.
            texteFoyers = Ecrire(fond, "Foyers");
            // Rien ne se coupe : le fond grandit avec le texte, et le débordement reste dessiné.
            texteFoyers.horizontalOverflow = HorizontalWrapMode.Overflow;
            texteFoyers.verticalOverflow = VerticalWrapMode.Overflow;
            texteFoyers.text = "";
            texteFoyers.gameObject.SetActive(false);
        }

        private static Text Ecrire(GameObject fond, string nom)
        {
            var ligne = new GameObject(nom, typeof(RectTransform));
            ligne.transform.SetParent(fond.transform, false);
            var t = ligne.AddComponent<Text>();
            t.font = Resources.GetBuiltinResource<Font>(POLICE);
            t.fontSize = TAILLE_POLICE;
            t.color = Color.white;
            return t;
        }
    }
}
