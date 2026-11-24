using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // La densité de chaque terre : ses habitants servis (`/monde`) divisés par son aire servie (`/carte`), deux nombres du monde
    // dont la vue ne fait que le rapport, pour que des terres de 7 000 et de 29 000 km² se comparent. L'échelle est logarithmique,
    // bornée aux terres du 5e et du 95e centile, la terre du milieu à mi-teinte : les quelques terres vides ou très denses ne
    // tassent pas toutes les autres dans la même teinte. La légende dit les bornes et la terre du milieu en hab./km², et
    // « jusqu'à » ou « dès » quand des terres dépassent une borne. Une terre sans aire servie rend le mode indisponible.
    public sealed class RepartitionHabitants
    {
        public const double CENTILE_BAS = .05, CENTILE_HAUT = .95;
        // Les deux bouts de l'échelle : le papier, et l'accent tiré vers l'encre.
        public static readonly Color CLAIRE = SocleInterface.Couleur("papier"), FONCEE = Color.Lerp(SocleInterface.Couleur("accent"), SocleInterface.Couleur("encre"), .3f);
        static readonly System.Globalization.CultureInfo Fr = System.Globalization.CultureInfo.GetCultureInfo("fr-FR");
        readonly Dictionary<long, double> densites = new Dictionary<long, double>();
        public double Minimum { get; }
        public double Maximum { get; }
        public double Bas { get; }
        public double Haut { get; }
        public string Legende { get; }
        public RepartitionHabitants(MondeLu monde, CarteLue carte)
        {
            if (monde == null) throw new ArgumentException("population non lue");
            if (carte == null) throw new ArgumentException("carte non lue");
            if (monde.Cellules.Count == 0 || monde.Cellules.Count != monde.CellCount)
                throw new ArgumentException("Population des territoires incomplète");
            var aires = new Dictionary<long, double>(); foreach (var c in carte.Cellules) aires[c.CellId] = c.AireKm2;
            foreach (var cellule in monde.Cellules)
            {
                if (cellule.Population < 0 || densites.ContainsKey(cellule.CellId))
                    throw new ArgumentException("Population négative ou territoire dupliqué");
                if (!aires.TryGetValue(cellule.CellId, out double aire)) throw new ArgumentException("Aire absente du territoire " + cellule.CellId);
                if (!(aire > 0)) throw new ArgumentException("aire des terres non servie par la carte");
                densites.Add(cellule.CellId, cellule.Population / aire);
            }
            var triees = densites.Values.OrderBy(n => n).ToList(); int dernier = triees.Count - 1;
            Minimum = triees[0]; Maximum = triees[dernier];
            Bas = triees[(int)Math.Floor(CENTILE_BAS * dernier)]; Haut = triees[(int)Math.Ceiling(CENTILE_HAUT * dernier)]; Mediane = triees[dernier / 2];
            Legende = "Densité : " + (Bas > Minimum ? "jusqu'à " : "") + Densite(Bas) + " (clair) → " + (AvecMediane ? Densite(Mediane) + " (mi-teinte) → " : "")
                + (Haut < Maximum ? "dès " : "") + Densite(Haut) + " (foncé) · " + TexteDuMonde.Date(monde.Date);
        }
        // Une densité comme on la lit : au dixième sous 10 hab./km², à l'unité au-delà.
        public static string Densite(double d) => (d < 10 ? Math.Round(d, 1, MidpointRounding.AwayFromZero).ToString("0.#", Fr) : TexteDuMonde.Nombre((long)Math.Round(d, MidpointRounding.AwayFromZero))) + " hab./km²";
        // La terre du milieu : la moitié des terres est moins dense, l'autre moitié plus. Elle prend la mi-teinte quand elle est entre les bornes.
        public double Mediane { get; }
        bool AvecMediane => Mediane > Bas && Mediane < Haut;
        // La densité de la terre, en habitants par km².
        public double DensiteDe(long cellId) => densites.TryGetValue(cellId, out double d) ? d : throw new ArgumentException("Population absente du territoire " + cellId);
        // De 0 (clair) à 1 (foncé), au logarithme : de la borne claire à la terre du milieu, puis de la terre du milieu à la borne foncée,
        // chacune sur une moitié de l'échelle ; au-delà d'une borne, la teinte de la borne.
        public float Position(long cellId)
        {
            double d = DensiteDe(cellId);
            if (Bas == Haut) return .5f;
            double n = Math.Min(Math.Max(d, Bas), Haut);
            float Entre(double a, double b) => (float)((Math.Log(1d + n) - Math.Log(1d + a)) / (Math.Log(1d + b) - Math.Log(1d + a)));
            return !AvecMediane ? Entre(Bas, Haut) : n <= Mediane ? .5f * Entre(Bas, Mediane) : .5f + .5f * Entre(Mediane, Haut);
        }
    }

    // La classe de relief servie de chaque terre (`/carte`), telle quelle : une teinte du socle par classe, du marais à la
    // haute montagne. Une terre sans relief servi, ou d'une classe que le socle ne connaît pas, est comptée et se peint en
    // gris ; une carte dont aucune terre n'a de relief servi n'en montre pas.
    public sealed class ReliefDesTerres
    {
        readonly Dictionary<long, int> classes = new Dictionary<long, int>(); // l'indice dans `SocleInterface.TeintesDuRelief`, -1 sans relief servi
        public int SansRelief { get; }
        public ReliefDesTerres(CarteLue carte)
        {
            if (carte == null || carte.Cellules.Count == 0) throw new ArgumentException("carte non lue");
            var table = SocleInterface.TeintesDuRelief;
            foreach (var cellule in carte.Cellules)
            {
                if (classes.ContainsKey(cellule.CellId)) throw new ArgumentException("territoire dupliqué dans la carte");
                int k = -1; for (int i = 0; i < table.Count; i++) if (table[i].classe == cellule.Relief) k = i;
                classes.Add(cellule.CellId, k); if (k < 0) SansRelief++;
            }
            if (SansRelief == classes.Count) throw new ArgumentException("relief non servi par la carte");
        }
        // La classe servie de la terre ; null sans relief servi.
        public string ClasseDe(long cellId) { int k = Indice(cellId); return k < 0 ? null : SocleInterface.TeintesDuRelief[k].classe; }
        public Color Teinte(long cellId) { int k = Indice(cellId); return k < 0 ? SocleInterface.Attenue : SocleInterface.TeintesDuRelief[k].teinte; }
        int Indice(long cellId) => classes.TryGetValue(cellId, out int k) ? k : throw new ArgumentException("Relief absent du territoire " + cellId);
        // Le relief servi ne change pas en cours de partie : sa légende le dit à la place d'une date.
        public string Legende
        {
            get { var t = SocleInterface.TeintesDuRelief; return "Relief servi, qui ne change pas : du " + t[0].nom + " (" + t[0].mot + ") à la " + t[t.Count - 1].nom + " (" + t[t.Count - 1].mot + ")" + (SansRelief > 0 ? " · gris : non servi" : ""); }
        }
        public string Detail => " " + string.Join(", ", SocleInterface.TeintesDuRelief.Select(t => t.nom + " en " + t.mot)) + "."
            + (SansRelief > 0 ? " En gris, " + CalquesCarte.Terres(SansRelief) + " sans relief servi." : "");
    }

    // Les jours de faim d'affilée et le manque de grain de chaque terre (`/monde`), tels que servis. Une terre à zéro jour de
    // faim a eu son grain ; -1 dit « non calculé », jamais « nourri ». La teinte suit les jours servis, de la première faim à la
    // plus longue du jour lu : aucun seuil n'est posé ici. Un monde dont aucune faim n'est calculée ne montre pas de vivres.
    public sealed class VivresDesTerres
    {
        public static readonly Color GRAIN = Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("or-vieilli"), .8f),
            PREMIERE_FAIM = Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("cuivre"), .75f),
            PLUS_LONGUE_FAIM = Color.Lerp(SocleInterface.Couleur("cuivre"), SocleInterface.Couleur("encre"), .6f);
        readonly Dictionary<long, long> jours = new Dictionary<long, long>();
        public DateDuMonde Date { get; }
        public long PlusLongueFaim { get; } // en jours ; 0 quand aucune terre n'a faim
        public int Affamees { get; }
        public int NonCalculees { get; }
        public double PlusGrosManqueKg { get; } = -1; // -1 : aucun manque calculé
        public VivresDesTerres(MondeLu monde)
        {
            if (monde == null) throw new ArgumentException("vivres non lus");
            if (monde.Cellules.Count == 0 || monde.Cellules.Count != monde.CellCount) throw new ArgumentException("Vivres des territoires incomplets");
            foreach (var cellule in monde.Cellules)
            {
                if (cellule.HungerTicks < -1 || cellule.FoodDeficitKg < 0 && cellule.FoodDeficitKg != -1 || jours.ContainsKey(cellule.CellId))
                    throw new ArgumentException("Faim négative ou territoire dupliqué");
                jours.Add(cellule.CellId, cellule.HungerTicks);
                if (cellule.HungerTicks < 0) NonCalculees++;
                else if (cellule.HungerTicks > 0) { Affamees++; PlusLongueFaim = Math.Max(PlusLongueFaim, cellule.HungerTicks); }
                if (cellule.FoodDeficitKg >= 0) PlusGrosManqueKg = Math.Max(PlusGrosManqueKg, cellule.FoodDeficitKg);
            }
            if (NonCalculees == jours.Count) throw new ArgumentException("faim non calculée par le monde");
            Date = monde.Date; TexteDuMonde.Date(Date);
        }
        // Les jours de faim servis de la terre ; -1 non calculé.
        public long JoursDe(long cellId) => jours.TryGetValue(cellId, out long j) ? j : throw new ArgumentException("Faim absente du territoire " + cellId);
        public Color Teinte(long cellId)
        {
            long j = JoursDe(cellId);
            return j < 0 ? SocleInterface.Attenue : j == 0 ? GRAIN : Color.Lerp(PREMIERE_FAIM, PLUS_LONGUE_FAIM, PlusLongueFaim <= 1 ? 1f : (j - 1f) / (PlusLongueFaim - 1f));
        }
        public string Legende => "Vivres au " + TexteDuMonde.Date(Date) + " · or : du grain" + (PlusLongueFaim > 1 ? " · faim : " + TexteDuMonde.Jours(1) + " (cuivre) → " + TexteDuMonde.Jours(PlusLongueFaim) + " (brun)"
            : PlusLongueFaim == 1 ? " · faim : " + TexteDuMonde.Jours(1) + " (cuivre)" : " partout") + (NonCalculees > 0 ? " · gris : non calculé" : "");
        public string Detail => "\n" + (Affamees > 0 ? CalquesCarte.Terres(Affamees) + (Affamees > 1 ? " ont" : " a") + " faim au " + TexteDuMonde.Date(Date) + " ; la plus longue faim dure " + TexteDuMonde.Jours(PlusLongueFaim)
                : "Aucune terre n'a faim au " + TexteDuMonde.Date(Date)) + (PlusGrosManqueKg > 0 ? " ; le plus lourd manque de grain servi est de " + TexteDuMonde.Masse(PlusGrosManqueKg) : "") + "."
            + (NonCalculees > 0 ? "\n" + CalquesCarte.Terres(NonCalculees) + " sans faim calculée, en gris." : "");
    }

    // Les guerres servies (`/guerres`) : les pays de l'agresseur et du défenseur de chacune, chaque maison ramenée au pays
    // des terres dont elle tient le bourg, et les terres qu'une armée assiège. Rien n'est déduit : un pays est en guerre
    // parce qu'une guerre servie le nomme.
    public sealed class BelligerantsDesPays
    {
        public static readonly Color ASSIEGEE = Color.Lerp(SocleInterface.Couleur("encre"), SocleInterface.Couleur("cuivre"), .35f), EN_PAIX = SocleInterface.Couleur("papier");
        readonly HashSet<string> enGuerre = new HashSet<string>(); readonly HashSet<long> assiegees = new HashSet<long>(); readonly List<string> lignes = new List<string>();
        public DateDuMonde Date { get; }
        public int Guerres { get; }
        public IReadOnlyCollection<string> PaysEnGuerre => enGuerre;
        public IReadOnlyCollection<long> TerresAssiegees => assiegees;
        // Les absences nomment ce qui manque : celles des lectures de la carte de la guerre, ou une lecture encore en vol.
        public BelligerantsDesPays(GuerresLues guerres, TerresDeLaCarte terres, string absenceDesGuerres = null, string absenceDesTerres = null)
        {
            if (guerres == null) throw new ArgumentException(absenceDesGuerres ?? "guerres en lecture");
            if (terres == null) throw new ArgumentException(absenceDesTerres ?? "pays en lecture");
            foreach (var guerre in guerres.Guerres)
            {
                string agresseur = CarteDeLaGuerre.PaysDeLaMaison(terres, guerre.Agresseur), defenseur = CarteDeLaGuerre.PaysDeLaMaison(terres, guerre.Defenseur);
                enGuerre.Add(agresseur); enGuerre.Add(defenseur);
                lignes.Add((terres.NomDuPays(agresseur) ?? "Un pays sans nom") + " contre " + (terres.NomDuPays(defenseur) ?? "un pays sans nom") + ".");
            }
            foreach (var armee in guerres.Armees) if (armee.Siege is long terre) assiegees.Add(terre);
            Guerres = guerres.Guerres.Count; Date = guerres.Date; TexteDuMonde.Date(Date);
        }
        public bool EnGuerre(string pays) => pays != null && enGuerre.Contains(pays);
        public Color Teinte(long cellId, string pays, Color pigment) => assiegees.Contains(cellId) ? ASSIEGEE : EnGuerre(pays) ? pigment : EN_PAIX;
        public string Legende => Guerres == 0 ? "Aucune guerre au " + TexteDuMonde.Date(Date) + " : tous les pays en paix, en papier"
            : "Guerres au " + TexteDuMonde.Date(Date) + " · en couleur : les pays en guerre · papier : en paix" + (assiegees.Count > 0 ? " · brun sombre : terre assiégée" : "");
        public string Detail => (lignes.Count > 0 ? "\n" + string.Join("\n", lignes) : "")
            + (assiegees.Count > 0 ? "\n" + CalquesCarte.Terres(assiegees.Count) + (assiegees.Count > 1 ? " assiégées." : " assiégée.") : "\nAucune terre assiégée.");
    }

    public enum ModeDeCarte { Politique, Relief, Population, Vivres, Guerres }

    // Ce qu'un mode lit pour se peindre, lu d'un coup avant qu'une seule terre change de couleur : une donnée qui manque lève
    // une `ArgumentException` qui la nomme, et le mode le dit au lieu de peindre. Les terres lues portent les pays, en
    // Politique comme dans les autres modes ; nulles, les pays ne sont pas lus.
    public sealed class LectureDuMode
    {
        public ModeDeCarte Mode { get; }
        public TerresDeLaCarte Terres { get; }
        public RepartitionHabitants Population { get; }
        public ReliefDesTerres Relief { get; }
        public VivresDesTerres Vivres { get; }
        public BelligerantsDesPays Guerres { get; }
        public LectureDuMode(ModeDeCarte mode, MondeLu monde, CarteLue carte, TerresDeLaCarte terres, GuerresLues guerres, string absenceDesTerres = null, string absenceDesGuerres = null)
        {
            Mode = mode; Terres = terres;
            if (mode == ModeDeCarte.Population) Population = new RepartitionHabitants(monde, carte);
            else if (mode == ModeDeCarte.Relief) Relief = new ReliefDesTerres(carte);
            else if (mode == ModeDeCarte.Vivres) Vivres = new VivresDesTerres(monde);
            else if (mode == ModeDeCarte.Guerres) Guerres = new BelligerantsDesPays(guerres, terres, absenceDesGuerres, absenceDesTerres);
        }
        public static LectureDuMode Lire(ModeDeCarte mode, MondeLu monde, CarteLue carte, CarteDeLaGuerre guerre) =>
            new LectureDuMode(mode, monde, carte, guerre?.Terres, guerre?.Guerres, guerre?.AbsenceDesTerres, guerre?.AbsenceDesGuerres);
        // Le mode couvre-t-il cette terre : sinon, l'exception qui le dit.
        public void Valider(long cellId)
        {
            if (Population != null) Population.Position(cellId); else if (Relief != null) Relief.ClasseDe(cellId); else if (Vivres != null) Vivres.JoursDe(cellId);
        }
        // La teinte d'une terre, ou d'un lieu d'une terre, qu'un pays tient et dont le pigment est donné ; la terre gardée en rouge.
        public Color Teinte(long cellId, string pays, Color pigment, bool retenue) => retenue ? SocleInterface.Couleur("alerte")
            : Mode == ModeDeCarte.Relief ? Relief.Teinte(cellId)
            : Mode == ModeDeCarte.Population ? Color.Lerp(RepartitionHabitants.CLAIRE, RepartitionHabitants.FONCEE, Population.Position(cellId))
            : Mode == ModeDeCarte.Vivres ? Vivres.Teinte(cellId)
            : Mode == ModeDeCarte.Guerres ? Guerres.Teinte(cellId, pays, pigment) : pigment;
        // La légende sur la carte : ce que dit chaque teinte, son unité et sa date, en trois lignes au plus.
        public string Legende(bool lieuxPeints) => Mode == ModeDeCarte.Politique
            ? (Terres != null ? CalquesCarte.LegendeDesPays(Terres) : CalquesCarte.PAYS_NON_LUS + CalquesCarte.ROUGE) + (lieuxPeints ? "\n" + LieuxDeCarte.ENTETE : "")
            : (Mode == ModeDeCarte.Relief ? Relief.Legende : Mode == ModeDeCarte.Population ? Population.Legende : Mode == ModeDeCarte.Vivres ? Vivres.Legende + " · " + CalquesCarte.FLECHES : Guerres.Legende) + CalquesCarte.ROUGE;
        // Le détail lu de l'infobulle : la règle du mode, puis ce que ses données disent.
        public string Detail => Mode == ModeDeCarte.Politique && Terres != null ? CalquesCarte.DetailDesPays(Terres)
            : CalquesCarte.DetailDuMode(Mode) + (Relief?.Detail ?? Vivres?.Detail ?? Guerres?.Detail ?? "");
    }

    public sealed class CalquesCarte : MonoBehaviour
    {
        // La bande des modes en bas à droite de la vue de la carte, sa légende juste au-dessus (unités de la toile, 1920 × 1080).
        public const string BANDE = "Modes de la carte", LEGENDE = "Légende du mode", COUPEE = "Mode indisponible : détail dans l'infobulle.";
        // Ce que toute légende finit par dire, la légende des pays qui ne sont pas encore lus, et celle des flèches du mode Vivres.
        public const string ROUGE = " · Rouge : territoire conservé", PAYS_NON_LUS = "Pays non lus", FLECHES = "orange : envoyé à votre siège";
        // La légende tient entre le guide des premiers gestes (jusqu'à x 764) et la fiche de la terre (dès x 1312).
        public const int LIGNES_MAX = 3; public const float FORCE_DU_LISERE = .55f; const float X = 776, LARGEUR = 530, BAS = 1004, MARGE = 4;
        // Le corps, en pixels sur un écran de 1080 de haut, d'un nom de ville et du nombre d'une armée : le même à toute
        // distance, jamais sous `POINTS_MIN`. Autour de l'encre, un liseré au papier du socle, large de `LISERE_PX`.
        public const float CORPS_DE_VILLE_PX = 17f, CORPS_DE_NOMBRE_PX = 19f, ECRAN_DE_REFERENCE_PX = 1080f, LISERE_PX = 1.2f, FORCE_DU_PAPIER = .85f;
        public const int POINTS_MIN = 9; public const string ETIQUETTES = "Étiquettes de la carte";
        CarteDessinee carte;
        Func<MondeLu> monde;
        Func<CelluleDeCarte> selection;
        Dictionary<long, Color> maisons; // la couleur de la maison de chaque terre dessinée, relevée une fois à la pose, jamais relue sur le terrain reteint
        Dictionary<long, string> departs; // le rattachement de chaque terre à la pose, relevé avec sa couleur : celui qui revient quand les pays ne sont pas lus
        TextMesh[] noms;
        // L'étiquette d'écran de chaque texte posé sur la carte, et la toile qui les porte, sur la caméra de la carte.
        readonly Dictionary<TextMesh, Text> ecrites = new Dictionary<TextMesh, Text>(); readonly Dictionary<Text, (string texte, int points, float largeur)> largeurs = new Dictionary<Text, (string, int, float)>();
        Canvas toileDesEtiquettes;
        readonly List<Rect> etiquettes = new List<Rect>(), nombres = new List<Rect>(), villes = new List<Rect>(), capitales = new List<Rect>();
        Text legende; RectTransform fond; Infobulle bulle;
        LieuxDeCarte lieux; FlechesDeCarte fleches; string ecrite, detaillee; LectureDuMode peinte; // la légende et le détail du dernier passage sans faute, et la lecture peinte ; nuls après une faute
        GuerresLues guerresPeintes; // les guerres lues au dernier passage du mode Guerres
        AtlasDeCarte atlas; VillesDeCarte villesDeCarte; int versionDesTextes = -1; CarteDeLaGuerre guerre; int versionDesPays = -1, coloriageDesPays = -1; // les pays servis des terres, leur version et celle de leurs couleurs au dernier passage
        MondeLu precedent;
        long? territoirePrecedent;
        bool changement = true;
        public ModeDeCarte Mode { get; private set; }
        public Text Legende => legende;
        // Ce que dit le bouton de chaque mode au survol : ce qu'il montre, jamais son nom seul.
        public static string PhraseDuMode(ModeDeCarte mode) => mode == ModeDeCarte.Politique ? "Politique : chaque terre à la couleur du pays qui la tient, avec son nom et ses frontières."
            : mode == ModeDeCarte.Relief ? "Relief : le terrain nu, du marais à la haute montagne, sans couleur ni frontière de pays."
            : mode == ModeDeCarte.Population ? "Population : chaque terre plus ou moins foncée selon ses habitants par km²."
            : mode == ModeDeCarte.Vivres ? "Vivres : qui a du grain et qui a faim, et ce que vos lieux envoient à votre siège."
            : "Guerres : seuls les pays en guerre en couleur, leurs armées et les terres assiégées.";
        public void Initialiser(CarteDessinee carte, Transform toile, Func<MondeLu> monde, Func<CelluleDeCarte> selection)
        {
            this.carte = carte; this.monde = monde; this.selection = selection;
            var bande = new GameObject(BANDE, typeof(RectTransform)).GetComponent<RectTransform>(); bande.SetParent(toile, false);
            bande.anchorMin = bande.anchorMax = bande.pivot = new Vector2(0, 1); bande.anchoredPosition = new Vector2(X + (LARGEUR - LARGEUR_DE_LA_BANDE) / 2f, -1012); bande.sizeDelta = new Vector2(LARGEUR_DE_LA_BANDE, SocleInterface.HauteurCommande);
            foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte))) Bouton(bande, mode);
            Enfoncer();
            var image = new GameObject(LEGENDE, typeof(RectTransform), typeof(Image)).GetComponent<Image>(); fond = image.rectTransform; fond.SetParent(toile, false);
            fond.anchorMin = fond.anchorMax = fond.pivot = new Vector2(0, 1); image.color = SocleInterface.Couleur("fond") * new Color(1f, 1f, 1f, .72f); image.raycastTarget = true; // pour l'infobulle
            bulle = fond.gameObject.AddComponent<Infobulle>(); legende = SocleInterface.Texte(fond, "Les calques attendent la carte…", 8, MARGE, LARGEUR - 16);
            legende.color = SocleInterface.Couleur("papier"); legende.supportRichText = false; legende.horizontalOverflow = HorizontalWrapMode.Wrap; legende.verticalOverflow = VerticalWrapMode.Overflow;
            Legender(legende.text, DetailDuMode(Mode));
        }
        public void Brancher(LieuxDeCarte lieux, FlechesDeCarte fleches, CarteDeLaGuerre guerre = null, AtlasDeCarte atlas = null, VillesDeCarte villes = null) { this.lieux = lieux; this.fleches = fleches; this.guerre = guerre; this.atlas = atlas; villesDeCarte = villes; }
        // Les cinq modes côte à côte, chacun réduit à son icône, la bande centrée sous la légende. L'icône est l'image de la
        // planche quand elle est livrée (`Planche`), le signe gravé du socle sinon.
        public const float LARGEUR_D_UN_MODE = 56, ECART_DES_MODES = 8, TRAIT_ENFONCE = 4, COTE_DE_L_ICONE = 32;
        public const string ICONES = "Forge/Icones/ModesDeCarte/", ICONE = "Icône ", TRAIT = "Trait du mode en cours";
        static readonly int MODES = Enum.GetValues(typeof(ModeDeCarte)).Length;
        public static readonly float LARGEUR_DE_LA_BANDE = MODES * LARGEUR_D_UN_MODE + (MODES - 1) * ECART_DES_MODES;
        readonly Dictionary<ModeDeCarte, (Button bouton, GameObject trait)> modes = new Dictionary<ModeDeCarte, (Button, GameObject)>();
        void Bouton(Transform bande, ModeDeCarte mode)
        {
            var b = SocleInterface.Commande(bande, mode.ToString(), (int)mode * (LARGEUR_D_UN_MODE + ECART_DES_MODES), 0, () => { Mode = mode; changement = true; Enfoncer(); }, phrase: PhraseDuMode(mode)); // un clic ne lit rien
            string motif = EmblemeCommande.Motif(mode.ToString()); EmblemeCommande.Reduire(b, motif, new Vector2(LARGEUR_D_UN_MODE, SocleInterface.HauteurCommande));
            var planche = Resources.Load<Texture2D>(Planche(mode));
            if (planche != null)
            {
                b.transform.Find("Repère " + motif).gameObject.SetActive(false);
                var icone = new GameObject(ICONE + motif, typeof(RectTransform), typeof(RawImage)); var cadre = (RectTransform)icone.transform; cadre.SetParent(b.transform, false);
                cadre.anchorMin = cadre.anchorMax = cadre.pivot = new Vector2(.5f, .5f); cadre.anchoredPosition = Vector2.zero; cadre.sizeDelta = new Vector2(COTE_DE_L_ICONE, COTE_DE_L_ICONE);
                var image = icone.GetComponent<RawImage>(); image.texture = planche; image.raycastTarget = false;
            }
            // L'état « sélection » du socle : un trait plein d'or vieilli de quatre pixels, sur la matière pressée. Le trait est un cadre
            // de quatre filets, enfants du bouton : la teinte du bouton, qui presse sa matière, ne l'assombrit pas.
            var trait = new GameObject(TRAIT, typeof(RectTransform)); var cadreDuTrait = (RectTransform)trait.transform; cadreDuTrait.SetParent(b.transform, false);
            cadreDuTrait.anchorMin = Vector2.zero; cadreDuTrait.anchorMax = Vector2.one; cadreDuTrait.offsetMin = cadreDuTrait.offsetMax = Vector2.zero;
            foreach (var (min, max) in new[] { (new Vector2(0, 0), new Vector2(1, 0)), (new Vector2(0, 1), new Vector2(1, 1)), (new Vector2(0, 0), new Vector2(0, 1)), (new Vector2(1, 0), new Vector2(1, 1)) })
            {
                var filet = new GameObject("Filet", typeof(RectTransform), typeof(Image)); var f = (RectTransform)filet.transform; f.SetParent(cadreDuTrait, false);
                f.anchorMin = min; f.anchorMax = max; f.pivot = new Vector2(min.x == max.x ? min.x : .5f, min.y == max.y ? min.y : .5f);
                f.sizeDelta = new Vector2(min.x == max.x ? TRAIT_ENFONCE : 0, min.y == max.y ? TRAIT_ENFONCE : 0); f.anchoredPosition = Vector2.zero;
                var image = filet.GetComponent<Image>(); image.color = SocleInterface.Couleur("or-vieilli"); image.raycastTarget = false;
            }
            trait.SetActive(false); modes[mode] = (b, trait);
        }
        // Le bouton du mode en cours est enfoncé, et lui seul.
        void Enfoncer()
        {
            foreach (var paire in modes)
            {
                bool enfonce = paire.Key == Mode; paire.Value.trait.SetActive(enfonce);
                var couleurs = paire.Value.bouton.colors; couleurs.normalColor = couleurs.selectedColor = SocleInterface.Couleur(enfonce ? "fond" : "secondaire"); if (!enfonce) couleurs.selectedColor = SocleInterface.Couleur("accent");
                paire.Value.bouton.colors = couleurs;
            }
        }
        public Button BoutonDu(ModeDeCarte mode) => modes[mode].bouton;
        // Le chemin, sous `Resources/`, de l'icône de la planche d'un mode : un fichier par mode, à son nom en minuscules (`politique.png`).
        public static string Planche(ModeDeCarte mode) => ICONES + mode.ToString().ToLowerInvariant();
        public bool Enfonce(ModeDeCarte mode) => modes[mode].trait.activeSelf;
        // Le liseré d'un pays le long de sa frontière : son pigment, tiré vers l'encre pour se lire sur sa propre teinte comme sur le papier.
        public static Color Lisere(Color pays) => LisereDuPigment(SocleInterface.Pigment(pays));
        public static Color LisereDuPigment(Color pigment) => Color.Lerp(pigment, SocleInterface.Couleur("encre"), FORCE_DU_LISERE);
        // La règle de chaque mode, dite dans l'infobulle de sa légende avant ce que ses données disent.
        public static string DetailDuMode(ModeDeCarte mode) => (mode == ModeDeCarte.Population ? "Plus une terre est foncée, plus elle est dense : ses habitants divisés par son aire, en habitants par km², pour que les terres petites et grandes se comparent. La mi-teinte est la terre du milieu : la moitié des terres est moins dense, l'autre moitié plus. L'échelle est logarithmique : chaque pas de teinte multiplie la densité au lieu de l'additionner, pour que les terres presque vides restent lisibles à côté des plus denses. Les terres les moins et les plus denses, un vingtième de chaque côté, prennent la teinte de la borne."
            : mode == ModeDeCarte.Relief ? "Le terrain nu : chaque terre porte la teinte de sa classe de relief servie, sans couleur ni frontière de pays, et les noms des pays se taisent."
            : mode == ModeDeCarte.Vivres ? "Une terre en or a eu son grain au dernier jour servi ; une terre qui a faim tire du cuivre au brun avec ses jours de faim d'affilée, jusqu'à la plus affamée. En gris, une terre dont le monde n'a pas encore calculé la faim. Les flèches partent de vos lieux vers votre siège, ou de votre siège vers celui de son suzerain, et s'épaississent avec ce qui est envoyé."
            : mode == ModeDeCarte.Guerres ? "Seuls les pays qu'une guerre servie nomme gardent leur couleur ; les autres passent au papier. Une terre qu'une armée assiège est en brun sombre."
            : "En attendant la lecture des pays, chaque terre porte, en pigment d'atlas, la couleur de la puissance relevée au dessin de la carte.") + " Le rouge marque la terre que vous gardez ouverte.";
        // Le nombre de terres, au pluriel quand il le faut.
        public static string Terres(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " terres" : " terre");
        // Les terres lues au pays servi : la légende de la carte politique se date du jour lu ; sans terres lues, elle dit les puissances du départ.
        public const string PAYS = "Chaque terre porte, en pigment d'atlas, la couleur de son pays, que ses voisins n'ont pas ; un vassal porte la teinte de son suzerain, plus claire. Une terre prise à un autre pays prend la couleur du preneur.";
        // Le détail de la carte politique quand les pays sont lus : la règle des couleurs, le liseré de chaque ensemble servi, puis la terre gardée.
        public static string DetailDesPays(TerresDeLaCarte terres)
        {
            var ensembles = terres.Pays.Select(p => p.Ensemble).Where(e => e != null).Distinct().OrderBy(e => e, StringComparer.Ordinal);
            return PAYS + string.Concat(ensembles.Select(e => " Un liseré " + SocleInterface.MotDuLisere(e) + " cerne les membres de l'ensemble « " + e + " ».")) + " Le rouge marque la terre que vous gardez ouverte.";
        }
        public static string LegendeDesPays(TerresDeLaCarte terres) => "Pays au " + TexteDuMonde.Date(terres.Date) + ROUGE;
        // L'infobulle d'un mode lu. Les lieux parlent dans la carte politique, les flèches dans les vivres : l'infobulle ne reprend
        // que leurs relevés, leur en-tête est déjà dans la légende ou dans la règle. La guerre parle dans chaque mode : les armées se voient partout.
        public static string DetailDuMode(LectureDuMode lecture, LieuxDeCarte lieux, FlechesDeCarte fleches, CarteDeLaGuerre guerre) => lecture.Detail
            + (lecture.Mode == ModeDeCarte.Politique && lieux != null && lieux.Peint ? lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length) : "")
            + (lecture.Mode == ModeDeCarte.Vivres && fleches != null ? "\n" + fleches.TexteLegende : "")
            + (guerre != null ? "\n" + guerre.TexteLegende : "");
        // Les lignes que prendrait `contenu` dans `texte`, à sa largeur, la toile à l'échelle donnée ; à hauteur nulle, une troncature ne compterait rien.
        public static int Lignes(Text texte, string contenu, float echelle)
        {
            var reglages = texte.GetGenerationSettings(new Vector2(texte.rectTransform.rect.width, 0)); reglages.scaleFactor = echelle; reglages.verticalOverflow = VerticalWrapMode.Overflow;
            var generateur = new TextGenerator(); generateur.Populate(contenu, reglages); return generateur.lineCount;
        }
        public void Legender(string texte, string detail)
        {
            int lignes = Math.Max(Lignes(legende, texte, 1f), Lignes(legende, texte, 2f / 3f));
            if (lignes > LIGNES_MAX) throw new ArgumentException("légende de " + lignes + " lignes : trois au plus");
            Ecrire(texte, texte + "\n" + detail);
        }
        void Ecrire(string texte, string infobulle)
        {
            legende.text = texte; bulle.phrase = infobulle; float hauteur = legende.preferredHeight; legende.rectTransform.sizeDelta = new Vector2(LARGEUR - 16, hauteur);
            fond.sizeDelta = new Vector2(LARGEUR, hauteur + 2 * MARGE); fond.anchoredPosition = new Vector2(X, -(BAS - hauteur - 2 * MARGE)); // le bas reste à y 1004, sur la bande
        }
        void LateUpdate()
        {
            if (legende == null || carte.CellulesPosees == 0) return;
            EspacerLesNoms();
            var lu = monde(); long? retenu = selection()?.CellId;
            // Les lieux et les flèches se lisent à leur rythme ; leur texte se récrit sans recolorer une terre. Après une faute, rien ne se récrit tant que rien ne bouge.
            // Le mode Guerres repeint aussi quand de nouvelles guerres sont lues : elles changent sans que les pays changent.
            int version = guerre != null ? guerre.Version : -1, coloriage = guerre != null ? guerre.Coloriage : -1; GuerresLues guerres = Mode == ModeDeCarte.Guerres ? guerre?.Guerres : null;
            if (!changement && ReferenceEquals(lu, precedent) && retenu == territoirePrecedent && version == versionDesPays && coloriage == coloriageDesPays && ReferenceEquals(guerres, guerresPeintes)) { if (ecrite != null) try { Recrire(peinte); } catch (ArgumentException) { changement = true; } return; }
            changement = false; precedent = lu; territoirePrecedent = retenu; versionDesPays = version; coloriageDesPays = coloriage; guerresPeintes = guerres; ecrite = null; peinte = null;
            try
            {
                if (maisons == null)
                {
                    maisons = new Dictionary<long, Color>(); departs = new Dictionary<long, string>();
                    foreach (var cellule in carte.Lue.Cellules) { Color? maison = carte.TeinteDe(cellule.CellId); if (maison.HasValue) { maisons.Add(cellule.CellId, maison.Value); departs.Add(cellule.CellId, carte.PaysDe(cellule.CellId)); } }
                    // La mer du terrain est celle du fond ; elle s'éclaircit un peu vers le papier au rivage, et les cimes tirent sur le papier.
                    Color mer = SocleInterface.Couleur("mer"), papier = SocleInterface.Couleur("papier");
                    carte.camera.backgroundColor = mer; carte.Habiller(mer, Color.Lerp(mer, papier, .11f), papier);
                    // Autour de la carte, la table du cabinet, et un cadre à l'or vieilli.
                    carte.Encadrer(SocleInterface.Couleur("fond"), SocleInterface.Couleur("or-vieilli"));
                    // Les traits du terrain à l'encre ; les lignes d'eau, une mer tirée vers le papier.
                    Color encre = SocleInterface.Couleur("encre"); carte.Encrer(encre, encre, encre, Color.Lerp(mer, papier, .45f));
                    ReleverLesNoms();
                }
                ModeDeCarte mode = Mode; var lecture = LectureDuMode.Lire(mode, lu, carte.Lue, guerre);
                if ((mode == ModeDeCarte.Population || mode == ModeDeCarte.Vivres) && maisons.Count != lu.Cellules.Count) throw new ArgumentException("Carte et monde ne couvrent pas les mêmes territoires");
                // Valider toutes les cellules avant de changer une seule couleur.
                foreach (long id in maisons.Keys) lecture.Valider(id);
                Peindre(lecture, retenu);
                Recrire(lecture); peinte = lecture;
            }
            catch (Exception e)
            {
                // Le mode dont la donnée manque le dit, et la carte politique se montre à sa place : jamais les couleurs d'un mode sous la légende d'un autre.
                ecrite = null; var politique = new LectureDuMode(ModeDeCarte.Politique, null, null, guerre?.Terres, null);
                if (maisons != null) Peindre(politique, retenu);
                string raison = Indisponible(Mode, e.Message), detail = politique.Detail;
                try { Legender(raison, detail); }
                catch (ArgumentException) { Ecrire(COUPEE, raison + "\n" + detail); } // trop longue pour trois lignes : entière dans l'infobulle
            }
        }
        // Chaque terre dessinée à la teinte du mode lu. Le pays servi et son liseré, sinon ceux de la puissance relevée au dessin :
        // la frontière suit le même pays que la teinte. En Relief, liserés, frontières et noms des pays s'effacent, les
        // rattachements restent.
        void Peindre(LectureDuMode lecture, long? retenu)
        {
            bool lus = lecture.Terres != null && guerre != null;
            foreach (var paire in maisons)
            {
                string pays = lus ? lecture.Terres.PaysDe(paire.Key) : departs[paire.Key];
                Color pigment = lus ? guerre.CouleurDuPays(pays) : SocleInterface.Pigment(paire.Value);
                carte.Rattacher(paire.Key, pays, lus ? guerre.LisereDuPays(pays) : LisereDuPigment(pigment));
                carte.Teinter(paire.Key, lecture.Teinte(paire.Key, pays, pigment, paire.Key == retenu));
                // Un lieu d'un autre pays que sa terre prend la couleur et le pays du sien, par la même règle qu'une cellule.
                if (lus)
                    foreach (var lieu in lecture.Terres.AutresPaysDe(paire.Key))
                    {
                        carte.RattacherLieu(paire.Key, lieu.Rang, lieu.Pays, guerre.LisereDuPays(lieu.Pays));
                        carte.TeinterLieu(paire.Key, lieu.Rang, lecture.Teinte(paire.Key, lieu.Pays, guerre.CouleurDuPays(lieu.Pays), paire.Key == retenu));
                    }
            }
            bool nu = lecture.Mode == ModeDeCarte.Relief; carte.MontrerLesPays(!nu); guerre?.MontrerLesNoms(!nu);
        }
        // Les textes posés sur la carte (les villes, les sièges de l'atlas), cachés compris, hors ceux de la guerre : relevés à la
        // pose de la carte, puis chaque fois que les villes en posent ou en retirent.
        void ReleverLesNoms()
        {
            var police = SocleInterface.Police(titre: true); versionDesTextes = villesDeCarte != null ? villesDeCarte.VersionDesTextes : -1;
            noms = carte.GetComponentsInChildren<TextMesh>(true).Where(n => guerre == null || !guerre.Possede(n.transform)).OrderBy(n => n.text, StringComparer.Ordinal).ToArray();
            foreach (var nom in noms)
            {
                nom.font = police; nom.fontSize = 16;
                nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                nom.color = SocleInterface.Couleur("encre");
            }
        }
        void Recrire(LectureDuMode lecture) { string texte = lecture.Legende(lieux != null && lieux.Peint), detail = DetailDuMode(lecture, lieux, fleches, guerre) + (atlas?.Absence != null ? "\nNoms de l'atlas non lus : " + TexteDuMonde.Absence(atlas.Absence) : "") + (villesDeCarte?.TexteLegende != null ? "\n" + villesDeCarte.TexteLegende : ""); if (texte != ecrite || detail != detaillee || Mathf.Abs(legende.preferredHeight - legende.rectTransform.sizeDelta.y) > 1f /* la toile peut changer d'échelle */) { Legender(texte, detail); ecrite = texte; detaillee = detail; } }

        // Ce qu'un mode dit quand sa donnée manque : laquelle, et que la carte politique se montre à sa place.
        public static string Indisponible(ModeDeCarte mode, string raison) => mode == ModeDeCarte.Politique
            ? "Pays indisponibles : " + TexteDuMonde.Absence(raison) + ". Couleurs des puissances du départ montrées."
            : "Mode " + mode + " indisponible : " + TexteDuMonde.Absence(raison) + ". Carte politique montrée.";
        // Un nom de ville ou le nombre d'une armée est un texte posé sur la carte, qui dit où il est et ce qu'il dit ; il se
        // lit sur une étiquette d'écran, au même corps quelle que soit la distance, nette et bordée d'un liseré clair, centrée
        // sur le point de l'écran où le texte se trouve. Le texte posé lui-même ne se dessine plus : couché sur le sol à une
        // taille en km, il devenait illisible sous une caméra inclinée. Son `enabled` dit toujours s'il est montré.
        // Les nombres des armées se montrent toujours ; puis les noms des villes, chacun seulement s'il ne recouvre rien de déjà montré.
        // Un nom de pays lisible réserve la place de chacune de ses lettres : un nom de ville ne s'écrit pas dessus, et revient
        // quand la vue s'approche et que le nom du pays s'efface.
        void EspacerLesNoms()
        {
            if (noms == null) return;
            if (villesDeCarte != null && villesDeCarte.VersionDesTextes != versionDesTextes) ReleverLesNoms();
            etiquettes.Clear();
            // Un texte retiré de la carte emporte son étiquette.
            bool parti = false; foreach (var paire in ecrites) if (paire.Key == null) { parti = true; break; }
            if (parti)
            {
                var gardees = ecrites.Where(p => p.Key != null).ToList(); foreach (var paire in ecrites) if (paire.Key == null && paire.Value != null) { largeurs.Remove(paire.Value); Detruire(paire.Value.gameObject); }
                ecrites.Clear(); foreach (var paire in gardees) ecrites.Add(paire.Key, paire.Value);
            }
            if (toileDesEtiquettes != null && carte.camera != null) toileDesEtiquettes.planeDistance = carte.camera.nearClipPlane * 1.5f;
            nombres.Clear(); villes.Clear(); capitales.Clear();
            if (guerre != null) { foreach (var nombre in guerre.NombresDesArmees) Espacer(nombre, true, CORPS_DE_NOMBRE_PX); nombres.AddRange(etiquettes); guerre.ReserverLesNoms(carte.camera, etiquettes); }
            // Les capitales passent avant l'atlas et les autres villes : seuls un nombre d'armée ou un nom de pays lisible les cachent.
            foreach (var nom in noms) if (villesDeCarte != null && villesDeCarte.EstCapitale(nom)) { int avant = etiquettes.Count; Espacer(nom, false, CORPS_DE_VILLE_PX); if (etiquettes.Count > avant) capitales.Add(etiquettes[etiquettes.Count - 1]); }
            atlas?.Ecriture?.Reserver(carte.camera, etiquettes); // les noms de l'atlas lisibles aussi
            foreach (var nom in noms) if (villesDeCarte == null || !villesDeCarte.EstCapitale(nom)) Espacer(nom, false, CORPS_DE_VILLE_PX);
        }
        // Les places, en pixels de l'écran, des nombres des armées montrés à la dernière image.
        public IReadOnlyList<Rect> PlacesDesNombres => nombres;
        // Les places, en pixels de l'écran, des noms de villes montrés à la dernière image.
        public IReadOnlyList<Rect> PlacesDesVilles => villes;
        // Les places des noms des capitales montrés à la dernière image (comptés aussi parmi les villes).
        public IReadOnlyList<Rect> PlacesDesCapitales => capitales;
        // L'étiquette d'écran d'un texte posé sur la carte ; null tant qu'il n'a pas été présenté.
        public Text EtiquetteDe(TextMesh nom) => nom != null && ecrites.TryGetValue(nom, out Text texte) ? texte : null;
        Text Etiqueter(TextMesh nom)
        {
            if (ecrites.TryGetValue(nom, out Text deja) && deja != null) return deja;
            if (toileDesEtiquettes == null)
            {
                // Sur la caméra de la carte, juste derrière son plan proche : une capture de cette caméra voit les étiquettes.
                // La toile n'est pas un enfant direct de la carte : le cabinet éteint toute toile qui l'est, hors la sienne.
                Transform porte = new GameObject(ETIQUETTES).transform; porte.SetParent(carte.transform, false);
                toileDesEtiquettes = new GameObject("Toile des étiquettes", typeof(RectTransform)).AddComponent<Canvas>(); toileDesEtiquettes.transform.SetParent(porte, false);
                toileDesEtiquettes.renderMode = RenderMode.ScreenSpaceCamera; toileDesEtiquettes.worldCamera = carte.camera; toileDesEtiquettes.sortingOrder = -1;
            }
            var texte = new GameObject(nom.name, typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(toileDesEtiquettes.transform, false);
            texte.font = SocleInterface.Police(titre: true); texte.color = SocleInterface.Couleur("encre"); texte.alignment = TextAnchor.MiddleCenter; texte.raycastTarget = false; texte.supportRichText = false;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow; texte.verticalOverflow = VerticalWrapMode.Overflow;
            var cadre = texte.rectTransform; cadre.anchorMin = cadre.anchorMax = Vector2.zero; cadre.pivot = new Vector2(.5f, .5f); cadre.sizeDelta = Vector2.zero;
            var lisere = texte.gameObject.AddComponent<Outline>(); Color papier = SocleInterface.Couleur("papier"); papier.a = FORCE_DU_PAPIER; lisere.effectColor = papier; lisere.effectDistance = new Vector2(LISERE_PX, -LISERE_PX);
            ecrites[nom] = texte; return texte;
        }
        // Aucune étiquette déjà montrée, ni aucune lettre d'un pays, n'est sous cette place.
        bool Libre(Rect place) { for (int k = 0; k < etiquettes.Count; k++) if (etiquettes[k].Overlaps(place)) return false; return true; }
        float Largeur(Text texte)
        {
            if (largeurs.TryGetValue(texte, out var connue) && connue.texte == texte.text && connue.points == texte.fontSize) return connue.largeur;
            float largeur = texte.preferredWidth; largeurs[texte] = (texte.text, texte.fontSize, largeur); return largeur;
        }
        static void Detruire(UnityEngine.Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
        void Espacer(TextMesh nom, bool toujours, float corpsPx)
        {
            if (nom == null) return;
            Camera camera = carte.camera; var rendu = nom.GetComponent<MeshRenderer>(); rendu.forceRenderingOff = true; Text texte = Etiqueter(nom);
            // Un texte posé qu'on a éteint (une ville cachée derrière une plus grande) n'a pas d'étiquette.
            if (!nom.gameObject.activeInHierarchy) { rendu.enabled = false; texte.enabled = false; return; }
            int points = Mathf.Max(POINTS_MIN, Mathf.RoundToInt(corpsPx * camera.pixelHeight / ECRAN_DE_REFERENCE_PX));
            if (texte.text != nom.text) texte.text = nom.text; if (texte.fontSize != points) texte.fontSize = points;
            Vector3 ecran = camera.WorldToScreenPoint(nom.transform.position); float largeur = Largeur(texte), hauteur = 1.3f * points;
            var rect = new Rect(ecran.x - largeur / 2f - 3f, ecran.y - hauteur / 2f - 2f, largeur + 6f, hauteur + 4f);
            // Derrière la caméra, rien ne se montre.
            bool visible = ecran.z > camera.nearClipPlane && (toujours || camera.pixelRect.Contains(rect.center) && Libre(rect));
            rendu.enabled = visible; texte.enabled = visible;
            if (!visible) return;
            etiquettes.Add(rect); if (!toujours) villes.Add(rect); texte.rectTransform.anchoredPosition = (Vector2)ecran - camera.pixelRect.min;
        }
    }
}
