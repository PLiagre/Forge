using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // L'échelle dessinée d'une légende : des teintes fondues de l'une à l'autre (`Degrade`), ou trois pastilles, et trois
    // étiquettes, de gauche à droite. Trois mots ou chiffres, jamais une phrase : la règle et la date sont dans l'infobulle.
    public sealed class EchelleDuMode
    {
        public IReadOnlyList<Color> Teintes { get; } public bool Degrade { get; } public IReadOnlyList<string> Etiquettes { get; }
        public EchelleDuMode(bool degrade, IReadOnlyList<Color> teintes, string gauche, string milieu, string droite)
        {
            if (teintes == null || (degrade ? teintes.Count < 2 : teintes.Count != 3)) throw new ArgumentException(degrade ? "un dégradé de deux teintes au moins" : "trois pastilles");
            var etiquettes = new[] { gauche, milieu, droite }; if (etiquettes.Any(string.IsNullOrWhiteSpace)) throw new ArgumentException("trois étiquettes non vides");
            Degrade = degrade; Teintes = teintes.ToArray(); Etiquettes = etiquettes;
        }
        // Les trois étiquettes, telles qu'elles se lisent sous l'échelle.
        public string Texte => string.Join(" · ", Etiquettes);
        // La valeur au rang `part` (0 à 1) d'une liste triée : au plancher sous la médiane, au plafond au-dessus, comme les bornes d'une échelle.
        public static double Centile(IReadOnlyList<double> triees, double part) { int dernier = triees.Count - 1; return triees[part <= .5 ? (int)Math.Floor(part * dernier) : (int)Math.Ceiling(part * dernier)]; }
    }

    // La densité de chaque lieu servi (`/lieux`) : ses habitants divisés par sa surface, deux nombres du monde dont la vue ne fait
    // que le rapport, pour que le bourg d'une cellule se lise à côté de ses campagnes. L'échelle est logarithmique, bornée aux
    // lieux du 5e et du 95e centile, le lieu du milieu à mi-teinte : les quelques lieux vides ou très denses ne tassent pas tous
    // les autres dans la même teinte. L'échelle dit les bornes et le lieu du milieu en hab./km², et « jusqu'à » ou « dès » quand
    // des lieux dépassent une borne.
    public sealed class RepartitionHabitants
    {
        public const double CENTILE_BAS = .05, CENTILE_HAUT = .95;
        // Les deux bouts de l'échelle : le papier, et le brun du socle tiré vers l'encre.
        public static readonly Color CLAIRE = SocleInterface.Couleur("papier"), FONCEE = Color.Lerp(SocleInterface.Couleur("secondaire"), SocleInterface.Couleur("encre"), .3f); // un brun d'encre : ni le bleu de la mer, ni le rouge de l'alerte
        static readonly System.Globalization.CultureInfo Fr = System.Globalization.CultureInfo.GetCultureInfo("fr-FR");
        readonly Dictionary<(long, long), double> densites = new Dictionary<(long, long), double>();
        public DateDuMonde Date { get; }
        public double Minimum { get; }
        public double Maximum { get; }
        public double Bas { get; }
        public double Haut { get; }
        // Le lieu du milieu : la moitié des lieux est moins dense, l'autre moitié plus. Il prend la mi-teinte quand il est entre les bornes.
        public double Mediane { get; }
        public int Lieux => densites.Count;
        public RepartitionHabitants(LieuxLus lieux)
        {
            if (lieux == null || lieux.Cellules.Count == 0) throw new ArgumentException("lieux non lus");
            foreach (var cellule in lieux.Cellules) foreach (var lieu in cellule.Lieux)
            {
                if (lieu.Population < 0 || !(lieu.SurfaceKm2 > 0)) throw new ArgumentException("Habitants négatifs ou surface nulle d'un lieu servi");
                densites.Add((cellule.CellId, lieu.Rang), lieu.Population / lieu.SurfaceKm2);
            }
            var triees = densites.Values.OrderBy(n => n).ToList();
            Minimum = triees[0]; Maximum = triees[triees.Count - 1]; Date = lieux.Date; TexteDuMonde.Date(Date);
            Bas = EchelleDuMode.Centile(triees, CENTILE_BAS); Haut = EchelleDuMode.Centile(triees, CENTILE_HAUT); Mediane = triees[(triees.Count - 1) / 2];
        }
        // Une densité comme on la lit : au dixième sous 10 hab./km², à l'unité au-delà.
        public static string Densite(double d) => (d < 10 ? Math.Round(d, 1, MidpointRounding.AwayFromZero).ToString("0.#", Fr) : TexteDuMonde.Nombre((long)Math.Round(d, MidpointRounding.AwayFromZero))) + " hab./km²";
        bool AvecMediane => Mediane > Bas && Mediane < Haut;
        // La densité du lieu, en habitants par km².
        public double DensiteDe(long cellId, long rang) => densites.TryGetValue((cellId, rang), out double d) ? d : throw new ArgumentException("Habitants absents du lieu " + rang + " du territoire " + cellId);
        public bool Sert(long cellId, long rang) => densites.ContainsKey((cellId, rang));
        // De 0 (clair) à 1 (foncé), au logarithme : de la borne claire au lieu du milieu, puis du lieu du milieu à la borne foncée,
        // chacun sur une moitié de l'échelle ; au-delà d'une borne, la teinte de la borne.
        public float Position(long cellId, long rang)
        {
            double d = DensiteDe(cellId, rang);
            if (Bas == Haut) return .5f;
            double n = Math.Min(Math.Max(d, Bas), Haut);
            float Entre(double a, double b) => (float)((Math.Log(1d + n) - Math.Log(1d + a)) / (Math.Log(1d + b) - Math.Log(1d + a)));
            return !AvecMediane ? Entre(Bas, Haut) : n <= Mediane ? .5f * Entre(Bas, Mediane) : .5f + .5f * Entre(Mediane, Haut);
        }
        public EchelleDuMode Echelle => new EchelleDuMode(true, new[] { CLAIRE, FONCEE }, (Bas > Minimum ? "jusqu'à " : "") + Densite(Bas), Densite(Mediane), (Haut < Maximum ? "dès " : "") + Densite(Haut));
        public string Detail => " Habitants au " + TexteDuMonde.Date(Date) + ", sur " + TexteDuMonde.Nombre(Lieux) + " lieux.";
    }

    // La classe de relief servie de chaque terre (`/carte`), telle quelle : une teinte du socle par classe, du marais à la
    // haute montagne. Le terrain la dessine par l'altitude qu'il en a levée, fondue d'une classe à l'autre ; la teinte de la
    // classe reste celle de la terre sous un éclat. Une terre sans relief servi, ou d'une classe que le socle ne connaît pas,
    // est comptée et se peint en gris ; une carte dont aucune terre n'a de relief servi n'en montre pas.
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
        // Les teintes des classes, de la plus basse à la plus haute : les paliers de la teinte d'altitude.
        public static Color[] Paliers => SocleInterface.TeintesDuRelief.Select(t => t.teinte).ToArray();
        // L'échelle fond les classes de la plus basse à la plus haute ; la basse, celle du milieu et la haute la nomment.
        public EchelleDuMode Echelle { get { var t = SocleInterface.TeintesDuRelief; return new EchelleDuMode(true, Paliers, t[0].nom, t[t.Count / 2].nom, t[t.Count - 1].nom); } }
        // Le relief servi ne change pas en cours de partie : l'infobulle le dit à la place d'une date.
        public string Detail => " Le relief servi ne change pas en cours de partie : " + string.Join(", ", SocleInterface.TeintesDuRelief.Select(t => t.nom + " en " + t.mot)) + "."
            + (SansRelief > 0 ? " " + CalquesCarte.Terres(SansRelief) + " sans relief servi se dessinent en plaine." : "");
    }

    // Les jours de grain qui restent à chaque lieu servi (`/lieux`), tels que le mieux-vivre les lit : la nourriture moins la dette,
    // divisée par la ration de ses habitants. La teinte va du vide (aucune réserve, ou une dette) au plein, la borne haute étant
    // la réserve du 95e centile des lieux servis : aucun seuil n'est posé ici. Un lieu sans habitants n'a pas de réserve : gris.
    public sealed class VivresDesLieux
    {
        public const double CENTILE_HAUT = .95;
        public static readonly Color PLEIN = Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("or-vieilli"), .8f),
            VIDE = Color.Lerp(SocleInterface.Couleur("cuivre"), SocleInterface.Couleur("encre"), .6f);
        readonly Dictionary<(long, long), double?> reserves = new Dictionary<(long, long), double?>();
        public DateDuMonde Date { get; }
        public double Haut { get; } // en jours, la borne pleine ; 0 quand aucun lieu n'a de réserve
        public double Mediane { get; }
        public double Maximum { get; }
        public int Vides { get; } // lieux habités sans réserve, ou endettés
        public int SansHabitants { get; }
        public VivresDesLieux(LieuxLus lieux)
        {
            if (lieux == null || lieux.Cellules.Count == 0) throw new ArgumentException("lieux non lus");
            var servies = new List<double>();
            foreach (var cellule in lieux.Cellules) foreach (var lieu in cellule.Lieux)
            {
                reserves.Add((cellule.CellId, lieu.Rang), lieu.ReserveJours);
                if (lieu.ReserveJours is double r) { servies.Add(Math.Max(r, 0)); if (r <= 0) Vides++; } else SansHabitants++;
            }
            if (servies.Count == 0) throw new ArgumentException("aucun lieu habité servi");
            servies.Sort(); Haut = EchelleDuMode.Centile(servies, CENTILE_HAUT); Mediane = servies[(servies.Count - 1) / 2]; Maximum = servies[servies.Count - 1];
            Date = lieux.Date; TexteDuMonde.Date(Date);
        }
        // Les jours de réserve servis du lieu ; null sans habitants.
        public double? JoursDe(long cellId, long rang) => reserves.TryGetValue((cellId, rang), out double? j) ? j : throw new ArgumentException("Réserve absente du lieu " + rang + " du territoire " + cellId);
        public bool Sert(long cellId, long rang) => reserves.ContainsKey((cellId, rang));
        // De 0 (vide) à 1 (plein) : la réserve rapportée à la borne haute ; au-delà, plein.
        public float Position(long cellId, long rang) { double? j = JoursDe(cellId, rang); return j == null || !(Haut > 0) ? 0f : (float)Math.Min(1, Math.Max(0, j.Value) / Haut); }
        public Color Teinte(long cellId, long rang) => JoursDe(cellId, rang) == null ? SocleInterface.Attenue : Color.Lerp(VIDE, PLEIN, Position(cellId, rang));
        static string Jours(double j) => TexteDuMonde.Jours((long)Math.Round(j, MidpointRounding.AwayFromZero));
        public EchelleDuMode Echelle => new EchelleDuMode(true, new[] { VIDE, PLEIN }, "vide", Jours(Mediane), (Maximum > Haut ? "dès " : "") + Jours(Haut));
        public string Detail => "\nRéserves au " + TexteDuMonde.Date(Date) + " : " + (Vides > 0 ? TexteDuMonde.Nombre(Vides) + (Vides > 1 ? " lieux habités sont vides" : " lieu habité est vide") : "aucun lieu habité n'est vide")
            + " ; la moitié des lieux habités a moins de " + Jours(Mediane) + " de grain." + (SansHabitants > 0 ? "\n" + TexteDuMonde.Nombre(SansHabitants) + (SansHabitants > 1 ? " lieux sans habitants, en gris." : " lieu sans habitants, en gris.") : "");
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
        public int Armees { get; }
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
            Guerres = guerres.Guerres.Count; Armees = guerres.Armees.Count; Date = guerres.Date; TexteDuMonde.Date(Date);
        }
        public bool EnGuerre(string pays) => pays != null && enGuerre.Contains(pays);
        public Color Teinte(long cellId, string pays, Color pigment) => assiegees.Contains(cellId) ? ASSIEGEE : EnGuerre(pays) ? pigment : EN_PAIX;
        // Sans guerre ni armée servie, il n'y a rien à échelonner : la légende le dit.
        public const string AUCUNE_ARMEE = "Aucune armée en campagne";
        public bool EnCampagne => Guerres > 0 || Armees > 0;
        public EchelleDuMode Echelle => EnCampagne ? new EchelleDuMode(false, new[] { CalquesCarte.PIGMENT_TEMOIN, EN_PAIX, ASSIEGEE }, "en guerre", "en paix", "assiégée") : null;
        public string Detail => "\n" + (EnCampagne ? "Guerres au " : "Aucune guerre ni armée servie au ") + TexteDuMonde.Date(Date) + "." + (lignes.Count > 0 ? "\n" + string.Join("\n", lignes) : "")
            + (assiegees.Count > 0 ? "\n" + CalquesCarte.Terres(assiegees.Count) + (assiegees.Count > 1 ? " assiégées." : " assiégée.") : "\nAucune terre assiégée.");
    }

    public enum ModeDeCarte { Politique, Relief, Population, Vivres, Guerres }

    // Ce qu'un mode lit pour se peindre, lu d'un coup avant qu'un seul lieu change de couleur : une donnée qui manque lève une
    // `ArgumentException` qui la nomme, et le mode le dit au lieu de peindre. Les terres lues portent les pays, en Politique
    // comme dans les autres modes ; nulles, les pays ne sont pas lus. Population et Vivres se lisent lieu par lieu (`/lieux`) ;
    // la carte politique peint en rouge les seuls lieux du joueur en alerte (`alertes`), et rien d'autre.
    public sealed class LectureDuMode
    {
        public ModeDeCarte Mode { get; }
        public TerresDeLaCarte Terres { get; }
        public RepartitionHabitants Population { get; }
        public ReliefDesTerres Relief { get; }
        public VivresDesLieux Vivres { get; }
        public BelligerantsDesPays Guerres { get; }
        readonly HashSet<(long, long)> alertes;
        public LectureDuMode(ModeDeCarte mode, LieuxLus lieux, CarteLue carte, TerresDeLaCarte terres, GuerresLues guerres, IEnumerable<(long cell, long rang)> alertes = null,
            string absenceDesLieux = null, string absenceDesTerres = null, string absenceDesGuerres = null)
        {
            Mode = mode; Terres = terres; this.alertes = new HashSet<(long, long)>(alertes ?? new (long, long)[0]);
            if ((mode == ModeDeCarte.Population || mode == ModeDeCarte.Vivres) && lieux == null) throw new ArgumentException(absenceDesLieux ?? "lieux en lecture");
            if (mode == ModeDeCarte.Population) Population = new RepartitionHabitants(lieux);
            else if (mode == ModeDeCarte.Relief) Relief = new ReliefDesTerres(carte);
            else if (mode == ModeDeCarte.Vivres) Vivres = new VivresDesLieux(lieux);
            else if (mode == ModeDeCarte.Guerres) Guerres = new BelligerantsDesPays(guerres, terres, absenceDesGuerres, absenceDesTerres);
        }
        public static LectureDuMode Lire(ModeDeCarte mode, Lecture<LieuxLus> lieux, CarteLue carte, CarteDeLaGuerre guerre, IEnumerable<(long cell, long rang)> alertes = null) =>
            new LectureDuMode(mode, lieux != null && lieux.Presente ? lieux.Donnees : null, carte, guerre?.Terres, guerre?.Guerres, alertes, lieux?.Absence, guerre?.AbsenceDesTerres, guerre?.AbsenceDesGuerres);
        // Le mode couvre-t-il ce lieu : sinon, l'exception qui le dit.
        public void Valider(long cellId, long rang)
        {
            if (Population != null && !Population.Sert(cellId, rang) || Vivres != null && !Vivres.Sert(cellId, rang)) throw new ArgumentException("Lieu " + rang + " du territoire " + cellId + " non servi");
            if (Relief != null) Relief.ClasseDe(cellId);
        }
        public bool EnAlerte(long cellId, long rang) => alertes.Contains((cellId, rang));
        // La teinte d'un lieu qu'un pays tient et dont le pigment est donné.
        public Color Teinte(long cellId, long rang, string pays, Color pigment) => Mode == ModeDeCarte.Relief ? Relief.Teinte(cellId)
            : Mode == ModeDeCarte.Population ? Color.Lerp(RepartitionHabitants.CLAIRE, RepartitionHabitants.FONCEE, Population.Position(cellId, rang))
            : Mode == ModeDeCarte.Vivres ? Vivres.Teinte(cellId, rang)
            : Mode == ModeDeCarte.Guerres ? Guerres.Teinte(cellId, pays, pigment)
            : EnAlerte(cellId, rang) ? SocleInterface.Couleur("alerte") : pigment;
        // L'échelle de la légende ; nulle quand il n'y a rien à échelonner (aucune armée en campagne).
        public EchelleDuMode Echelle => Mode == ModeDeCarte.Politique ? new EchelleDuMode(false, new[] { CalquesCarte.PIGMENT_TEMOIN, SocleInterface.Couleur("alerte"), SocleInterface.Couleur("encre") },
                Terres != null ? "pays" : "puissance", CalquesCarte.ALERTE, CalquesCarte.TERRE_OUVERTE)
            : Relief?.Echelle ?? Population?.Echelle ?? Vivres?.Echelle ?? Guerres.Echelle;
        // La légende telle qu'elle se lit : les étiquettes de l'échelle, ou ce qui en tient lieu.
        public string Legende => Echelle?.Texte ?? BelligerantsDesPays.AUCUNE_ARMEE;
        // Le détail lu de l'infobulle : la règle du mode, puis ce que ses données disent.
        public string Detail => Mode == ModeDeCarte.Politique ? (Terres != null ? CalquesCarte.DetailDesPays(Terres) : CalquesCarte.DetailDuMode(Mode))
            : CalquesCarte.DetailDuMode(Mode) + (Relief?.Detail ?? Population?.Detail ?? Vivres?.Detail ?? Guerres?.Detail ?? "");
    }

    public sealed class CalquesCarte : MonoBehaviour
    {
        // La bande des modes en bas à droite de la vue de la carte, sa légende juste au-dessus (unités de la toile, 1920 × 1080).
        public const string BANDE = "Modes de la carte", LEGENDE = "Légende du mode", COUPEE = "Mode indisponible : détail dans l'infobulle.";
        // Les étiquettes de l'échelle politique : le rouge n'y dit que l'alerte, et la terre ouverte est cernée d'un trait d'encre.
        // `PAYS_NON_LUS` ouvre le détail quand les pays ne sont pas encore lus.
        public const string ALERTE = "rouge : départs", TERRE_OUVERTE = "trait : terre ouverte", PAYS_NON_LUS = "Pays non lus";
        // La pastille d'un pays dans une échelle : un pigment d'atlas, qu'aucun mode ne prend pour l'une de ses teintes.
        public static readonly Color PIGMENT_TEMOIN = SocleInterface.Pigment(new Color(.45f, .6f, .85f));
        // La légende tient entre le guide des premiers gestes (jusqu'à x 764) et la fiche de la terre (dès x 1312) : une échelle haute
        // de `HAUTEUR_D_ECHELLE`, ses trois étiquettes dessous ; un message, sans échelle, en trois lignes au plus.
        public const int LIGNES_MAX = 3; public const float FORCE_DU_LISERE = .55f, HAUTEUR_D_ECHELLE = 12f; const float X = 776, LARGEUR = 530, BAS = 1004, MARGE = 4;
        public const string ECHELLE = "Échelle du mode", ETIQUETTE = "Étiquette ";
        // Les lieux servis se relisent toutes les `PERIODE_DES_LIEUX_S` tant que Population ou Vivres est montré.
        public const float PERIODE_DES_LIEUX_S = 2f;
        // Le corps, en pixels sur un écran de 1080 de haut, d'un nom de ville et du nombre d'une armée : le même à toute
        // distance, jamais sous `POINTS_MIN`. Autour de l'encre, un liseré au papier du socle, large de `LISERE_PX`.
        public const float CORPS_DE_VILLE_PX = 17f, CORPS_DE_NOMBRE_PX = 19f, ECRAN_DE_REFERENCE_PX = 1080f, LISERE_PX = 1.2f, FORCE_DU_PAPIER = .85f;
        public const int POINTS_MIN = 9; public const string ETIQUETTES = "Étiquettes de la carte";
        CarteDessinee carte;
        Dictionary<long, Color> maisons; // la couleur de la maison de chaque terre dessinée, relevée une fois à la pose, jamais relue sur le terrain reteint
        Dictionary<long, string> departs; // le rattachement de chaque terre à la pose, relevé avec sa couleur : celui qui revient quand les pays ne sont pas lus
        Dictionary<long, long[]> rangsDesLieux; // les rangs des lieux que le terrain dessine, par terre
        RawImage echelle; Texture2D teintesDeLEchelle; readonly Text[] etiquettesDeLEchelle = new Text[3];
        // Les lieux servis, la lecture en vol, et la prochaine ; nulles tant qu'aucune n'a rendu.
        public Func<Lecture<LieuxLus>> LecteurDesLieux; public bool LieuxEnVol => volDesLieux != null && !volDesLieux.IsCompleted; public Lecture<LieuxLus> LieuxLus { get; private set; }
        System.Threading.Tasks.Task<Lecture<LieuxLus>> volDesLieux; double prochaineDesLieux; Lecture<LieuxLus> lieuxPeints; int alertesPeintes = -1;
        TerresDeLaCarte terresEcrites; // les terres dont la légende écrite tient sa date
        TextMesh[] noms;
        // L'étiquette d'écran de chaque texte posé sur la carte, et la toile qui les porte, sur la caméra de la carte.
        readonly Dictionary<TextMesh, Text> ecrites = new Dictionary<TextMesh, Text>(); readonly Dictionary<Text, (string texte, int points, float largeur)> largeurs = new Dictionary<Text, (string, int, float)>();
        Canvas toileDesEtiquettes;
        readonly List<Rect> etiquettes = new List<Rect>(), nombres = new List<Rect>(), villes = new List<Rect>(), capitales = new List<Rect>();
        Text legende; RectTransform fond; Infobulle bulle;
        LieuxDeCarte lieux; FlechesDeCarte fleches; string ecrite, detaillee; LectureDuMode peinte; // la légende et le détail du dernier passage sans faute, et la lecture peinte ; nuls après une faute
        GuerresLues guerresPeintes; // les guerres lues au dernier passage du mode Guerres
        AtlasDeCarte atlas; VillesDeCarte villesDeCarte; int versionDesTextes = -1; CarteDeLaGuerre guerre; int versionDesPays = -1, coloriageDesPays = -1; // les pays servis des terres, leur version et celle de leurs couleurs au dernier passage
        bool changement = true;
        public ModeDeCarte Mode { get; private set; }
        // Le texte de la légende : les trois étiquettes de l'échelle jointes, ou le message quand il n'y a pas d'échelle. Le texte
        // ne se montre qu'avec un message ; l'échelle montre ses étiquettes elle-même.
        public Text Legende => legende;
        public EchelleDuMode EchelleMontree { get; private set; }
        public RawImage Echelle => echelle;
        public IReadOnlyList<Text> EtiquettesDeLEchelle => etiquettesDeLEchelle;
        // Ce que dit le bouton de chaque mode au survol : ce qu'il montre, jamais son nom seul.
        public static string PhraseDuMode(ModeDeCarte mode) => mode == ModeDeCarte.Politique ? "Politique : chaque lieu à la couleur du pays qui le tient ; en rouge, vos lieux d'où partent plus de gens qu'il n'en arrive."
            : mode == ModeDeCarte.Relief ? "Relief : le terrain nu, teint par son altitude du marais à la haute montagne, sans couleur ni frontière de pays."
            : mode == ModeDeCarte.Population ? "Population : chaque lieu plus ou moins foncé selon ses habitants par km², les villes sombres, les campagnes claires."
            : mode == ModeDeCarte.Vivres ? "Vivres : les jours de grain qui restent à chaque lieu, et ce que vos lieux envoient à votre siège."
            : "Guerres : seuls les pays en guerre en couleur, leurs armées et les terres assiégées.";
        public void Initialiser(CarteDessinee carte, Transform toile, Func<MondeLu> monde, Func<CelluleDeCarte> selection)
        {
            this.carte = carte; // le monde et la terre gardée ne se lisent plus ici : les lieux servis se lisent à part, et la terre gardée se cerne par la marque de la carte
            var bande = new GameObject(BANDE, typeof(RectTransform)).GetComponent<RectTransform>(); bande.SetParent(toile, false);
            bande.anchorMin = bande.anchorMax = bande.pivot = new Vector2(0, 1); bande.anchoredPosition = new Vector2(X + (LARGEUR - LARGEUR_DE_LA_BANDE) / 2f, -1012); bande.sizeDelta = new Vector2(LARGEUR_DE_LA_BANDE, SocleInterface.HauteurCommande);
            foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte))) Bouton(bande, mode);
            Enfoncer();
            var image = new GameObject(LEGENDE, typeof(RectTransform), typeof(Image)).GetComponent<Image>(); fond = image.rectTransform; fond.SetParent(toile, false);
            fond.anchorMin = fond.anchorMax = fond.pivot = new Vector2(0, 1); image.color = SocleInterface.Couleur("fond") * new Color(1f, 1f, 1f, .72f); image.raycastTarget = true; // pour l'infobulle
            foreach (var (bouton, _) in modes.Values) bouton.GetComponent<Infobulle>().eviter = fond; // l'infobulle d'un mode ne recouvre pas la légende
            bulle = fond.gameObject.AddComponent<Infobulle>(); legende = SocleInterface.Texte(fond, "Les calques attendent la carte…", 8, MARGE, LARGEUR - 16);
            legende.color = SocleInterface.Couleur("papier"); legende.supportRichText = false; legende.horizontalOverflow = HorizontalWrapMode.Wrap; legende.verticalOverflow = VerticalWrapMode.Overflow;
            // L'échelle : une bande de teintes sur toute la largeur, et trois étiquettes dessous, à gauche, au milieu, à droite.
            echelle = new GameObject(ECHELLE, typeof(RectTransform), typeof(RawImage)).GetComponent<RawImage>(); var bandeau = echelle.rectTransform; bandeau.SetParent(fond, false);
            bandeau.anchorMin = bandeau.anchorMax = bandeau.pivot = new Vector2(0, 1); bandeau.anchoredPosition = new Vector2(8, -MARGE - 2); bandeau.sizeDelta = new Vector2(LARGEUR - 16, HAUTEUR_D_ECHELLE); echelle.raycastTarget = false;
            teintesDeLEchelle = new Texture2D(256, 1, TextureFormat.RGBA32, false) { name = ECHELLE, wrapMode = TextureWrapMode.Clamp }; echelle.texture = teintesDeLEchelle;
            var places = new[] { (TextAnchor.UpperLeft, "gauche"), (TextAnchor.UpperCenter, "milieu"), (TextAnchor.UpperRight, "droite") };
            for (int k = 0; k < 3; k++)
            {
                var etiquette = SocleInterface.Texte(fond, "", 8 + k * (LARGEUR - 16) / 3f, MARGE + 2 + HAUTEUR_D_ECHELLE + 2, (LARGEUR - 16) / 3f); etiquette.name = ETIQUETTE + places[k].Item2;
                etiquette.alignment = places[k].Item1; etiquette.color = SocleInterface.Couleur("papier"); etiquette.supportRichText = false; etiquette.horizontalOverflow = HorizontalWrapMode.Overflow; etiquette.raycastTarget = false;
                etiquettesDeLEchelle[k] = etiquette;
            }
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
        public static string DetailDuMode(ModeDeCarte mode) => (mode == ModeDeCarte.Population ? "Plus un lieu est foncé, plus il est dense : ses habitants divisés par sa surface, en habitants par km², pour que le bourg d'une terre se lise à côté de ses campagnes. La mi-teinte est le lieu du milieu : la moitié des lieux est moins dense, l'autre moitié plus. L'échelle est logarithmique : chaque pas de teinte multiplie la densité au lieu de l'additionner, pour que les lieux presque vides restent lisibles à côté des plus denses. Les lieux les moins et les plus denses, un vingtième de chaque côté, prennent la teinte de la borne."
            : mode == ModeDeCarte.Relief ? "Le terrain nu : chaque lieu prend la teinte de son altitude, fondue d'une classe de relief à l'autre, sans couleur ni frontière de pays, et les noms des pays se taisent."
            : mode == ModeDeCarte.Vivres ? "Chaque lieu dit les jours de grain qui lui restent pour nourrir ses habitants, sa dette ôtée : du brun quand il n'en a plus, à l'or quand il en a autant que les mieux pourvus, un vingtième des lieux habités au-delà. En gris, un lieu sans habitants. Les flèches partent de vos lieux vers votre siège, ou de votre siège vers celui de son suzerain, et s'épaississent avec ce qui est envoyé."
            : mode == ModeDeCarte.Guerres ? "Seuls les pays qu'une guerre servie nomme gardent leur couleur ; les autres passent au papier. Une terre qu'une armée assiège est en brun sombre."
            : PAYS_NON_LUS + " : en attendant leur lecture, chaque terre porte, en pigment d'atlas, la couleur de la puissance relevée au dessin de la carte. " + LieuxDeCarte.ENTETE) + TRAIT_DE_LA_TERRE_OUVERTE;
        public const string TRAIT_DE_LA_TERRE_OUVERTE = " La terre que vous gardez ouverte est cernée d'un trait d'encre.";
        // Le nombre de terres, au pluriel quand il le faut.
        public static string Terres(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " terres" : " terre");
        // Les terres lues au pays servi : la légende de la carte politique se date du jour lu ; sans terres lues, elle dit les puissances du départ.
        public const string PAYS = "Chaque terre porte, en pigment d'atlas, la couleur de son pays, que ses voisins n'ont pas ; un vassal porte la teinte de son suzerain, plus claire. Une terre prise à un autre pays prend la couleur du preneur.";
        // Le détail de la carte politique quand les pays sont lus : la date, la règle des couleurs, le liseré de chaque ensemble servi,
        // puis l'alerte et la terre gardée.
        public static string DetailDesPays(TerresDeLaCarte terres)
        {
            var ensembles = terres.Pays.Select(p => p.Ensemble).Where(e => e != null).Distinct().OrderBy(e => e, StringComparer.Ordinal);
            return "Pays au " + TexteDuMonde.Date(terres.Date) + ". " + PAYS + string.Concat(ensembles.Select(e => " Un liseré " + SocleInterface.MotDuLisere(e) + " cerne les membres de l'ensemble « " + e + " ».")) + " " + LieuxDeCarte.ENTETE + TRAIT_DE_LA_TERRE_OUVERTE;
        }
        // L'infobulle d'un mode lu. Les lieux parlent dans la carte politique, les flèches dans les vivres : l'infobulle reprend leurs
        // relevés, l'en-tête des lieux étant déjà dans la règle. La guerre parle dans chaque mode : les armées se voient partout.
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
        // Un message, sans échelle : trois lignes au plus.
        public void Legender(string texte, string detail)
        {
            int lignes = Math.Max(Lignes(legende, texte, 1f), Lignes(legende, texte, 2f / 3f));
            if (lignes > LIGNES_MAX) throw new ArgumentException("légende de " + lignes + " lignes : trois au plus");
            Ecrire(texte, texte + "\n" + detail, null);
        }
        // Une échelle et ses trois étiquettes, chacune sur une ligne, sans qu'aucune empiète sur sa voisine : sous des pastilles, chacune
        // tient dans son tiers ; sous un dégradé, celles des bouts et la moitié de celle du milieu tiennent chacune dans une moitié.
        public const float ECART_DES_ETIQUETTES = 8f;
        public void Legender(EchelleDuMode echelleDuMode, string detail)
        {
            foreach (string etiquette in echelleDuMode.Etiquettes) if (Math.Max(Lignes(legende, etiquette, 1f), Lignes(legende, etiquette, 2f / 3f)) > 1) throw new ArgumentException("étiquette de plus d'une ligne : " + etiquette);
            float pleine = LARGEUR - 16; var larges = echelleDuMode.Etiquettes.Select(e => Largeur(etiquettesDeLEchelle[0], e)).ToArray();
            bool tient = echelleDuMode.Degrade ? larges[0] + larges[1] / 2f + ECART_DES_ETIQUETTES <= pleine / 2f && larges[2] + larges[1] / 2f + ECART_DES_ETIQUETTES <= pleine / 2f
                : larges.All(l => l + ECART_DES_ETIQUETTES <= pleine / 3f);
            if (!tient) throw new ArgumentException("étiquettes qui empiètent l'une sur l'autre : " + echelleDuMode.Texte);
            Ecrire(echelleDuMode.Texte, echelleDuMode.Texte + "\n" + detail, echelleDuMode);
        }
        // La largeur que prendrait `contenu` écrit dans `texte`, sur une ligne.
        static float Largeur(Text texte, string contenu)
        {
            var reglages = texte.GetGenerationSettings(new Vector2(0, 0)); reglages.horizontalOverflow = HorizontalWrapMode.Overflow; reglages.scaleFactor = 1f;
            var generateur = new TextGenerator(); return generateur.GetPreferredWidth(contenu, reglages);
        }
        void Ecrire(string texte, string infobulle, EchelleDuMode echelleDuMode)
        {
            legende.text = texte; bulle.phrase = infobulle; EchelleMontree = echelleDuMode; float hauteur;
            legende.enabled = echelleDuMode == null; echelle.gameObject.SetActive(echelleDuMode != null);
            foreach (var etiquette in etiquettesDeLEchelle) etiquette.gameObject.SetActive(echelleDuMode != null);
            if (echelleDuMode == null) { hauteur = legende.preferredHeight; legende.rectTransform.sizeDelta = new Vector2(LARGEUR - 16, hauteur); }
            else
            {
                Teindre(echelleDuMode); float ligne = 0f;
                for (int k = 0; k < 3; k++)
                {
                    var etiquette = etiquettesDeLEchelle[k]; etiquette.text = echelleDuMode.Etiquettes[k];
                    // Sous des pastilles, chaque étiquette se centre sous la sienne ; sous un dégradé, elles tiennent ses deux bouts et son milieu.
                    etiquette.alignment = echelleDuMode.Degrade ? (k == 0 ? TextAnchor.UpperLeft : k == 1 ? TextAnchor.UpperCenter : TextAnchor.UpperRight) : TextAnchor.UpperCenter;
                    ligne = Mathf.Max(ligne, etiquette.preferredHeight); etiquette.rectTransform.sizeDelta = new Vector2((LARGEUR - 16) / 3f, etiquette.preferredHeight);
                }
                hauteur = 2 + HAUTEUR_D_ECHELLE + 2 + ligne;
            }
            fond.sizeDelta = new Vector2(LARGEUR, hauteur + 2 * MARGE); fond.anchoredPosition = new Vector2(X, -(BAS - hauteur - 2 * MARGE)); // le bas reste à y 1004, sur la bande
        }
        // La bande de l'échelle : les teintes fondues sur toute la largeur, ou trois pastilles égales.
        void Teindre(EchelleDuMode echelleDuMode)
        {
            int n = teintesDeLEchelle.width; var pixels = new Color[n]; var t = echelleDuMode.Teintes;
            for (int i = 0; i < n; i++)
            {
                float u = (i + .5f) / n;
                if (!echelleDuMode.Degrade) { pixels[i] = t[Math.Min(2, (int)(u * 3))]; continue; }
                float p = u * (t.Count - 1); int a = Math.Min(t.Count - 2, (int)p); pixels[i] = Color.Lerp(t[a], t[a + 1], p - a);
            }
            teintesDeLEchelle.filterMode = echelleDuMode.Degrade ? FilterMode.Bilinear : FilterMode.Point; teintesDeLEchelle.SetPixels(pixels); teintesDeLEchelle.Apply(false);
        }
        // Les lieux servis, relus hors du fil principal tant que Population ou Vivres est montré.
        void LireLesLieux(double t)
        {
            if (volDesLieux != null && volDesLieux.IsCompleted)
            {
                var fini = volDesLieux; volDesLieux = null;
                LieuxLus = fini.IsFaulted ? Lecture<LieuxLus>.Absent("lieux : " + fini.Exception.GetBaseException().Message) : fini.Result ?? Lecture<LieuxLus>.Absent("lieux : aucune réponse");
            }
            if (volDesLieux != null || !(Mode == ModeDeCarte.Population || Mode == ModeDeCarte.Vivres) || t < prochaineDesLieux) return;
            prochaineDesLieux = t + PERIODE_DES_LIEUX_S; var lire = LecteurDesLieux ?? LireDuService; volDesLieux = System.Threading.Tasks.Task.Run(lire);
        }
        Lecture<LieuxLus> LireDuService() { using (var client = new ClientLieux(carte.port, ClientLieux.DelaiMinimal)) return client.Lire(); }
        void LateUpdate()
        {
            if (legende == null || carte.CellulesPosees == 0) return;
            EspacerLesNoms();
            // La terre gardée est cernée à l'encre, quelle que soit la couleur que le cabinet a demandée : le rouge ne dit que l'alerte.
            if (carte.Marquee is long marquee) carte.Marquer(marquee, SocleInterface.Couleur("encre"));
            LireLesLieux(Time.realtimeSinceStartupAsDouble);
            // Les lieux et les flèches se lisent à leur rythme ; leur texte se récrit sans recolorer une terre. Après une faute, rien ne se récrit tant que rien ne bouge.
            // Le mode Guerres repeint aussi quand de nouvelles guerres sont lues : elles changent sans que les pays changent. Population et Vivres
            // repeignent à chaque lecture des lieux, la carte politique quand les alertes changent.
            int version = guerre != null ? guerre.Version : -1, coloriage = guerre != null ? guerre.Coloriage : -1; GuerresLues guerres = Mode == ModeDeCarte.Guerres ? guerre?.Guerres : null;
            var lieuxLus = Mode == ModeDeCarte.Population || Mode == ModeDeCarte.Vivres ? LieuxLus : null; int alertes = Mode == ModeDeCarte.Politique && lieux != null ? lieux.VersionDesAlertes : -1;
            // Des terres relues aux mêmes pays ne repeignent rien, mais leur date passe dans la légende : la lecture se refait pour le texte seul.
            if (!changement && ReferenceEquals(lieuxLus, lieuxPeints) && alertes == alertesPeintes && version == versionDesPays && coloriage == coloriageDesPays && ReferenceEquals(guerres, guerresPeintes))
            {
                if (ecrite != null) try { if (!ReferenceEquals(guerre?.Terres, terresEcrites)) { peinte = LectureDuMode.Lire(Mode, lieuxLus, carte.Lue, guerre, lieux?.EnAlerte); terresEcrites = guerre?.Terres; } Recrire(peinte); } catch (ArgumentException) { changement = true; }
                return;
            }
            changement = false; lieuxPeints = lieuxLus; alertesPeintes = alertes; versionDesPays = version; coloriageDesPays = coloriage; guerresPeintes = guerres; terresEcrites = guerre?.Terres; ecrite = null; peinte = null;
            try
            {
                if (maisons == null)
                {
                    maisons = new Dictionary<long, Color>(); departs = new Dictionary<long, string>(); rangsDesLieux = new Dictionary<long, long[]>(); var terrain = carte.Terrain;
                    for (int r = 0; r < carte.Lue.Cellules.Count; r++)
                    {
                        long id = carte.Lue.Cellules[r].CellId; Color? maison = carte.TeinteDe(id); if (!maison.HasValue) continue;
                        maisons.Add(id, maison.Value); departs.Add(id, carte.PaysDe(id));
                        var rangs = new long[terrain.LieuxDe(r)]; for (int k = 0; k < rangs.Length; k++) rangs[k] = terrain.RangDuLieu(terrain.PremierLieuDe(r) + k); rangsDesLieux.Add(id, rangs);
                    }
                    // La mer du terrain est celle du fond ; elle s'éclaircit un peu vers le papier au rivage, et les cimes tirent sur le papier.
                    Color mer = SocleInterface.Couleur("mer"), papier = SocleInterface.Couleur("papier");
                    carte.camera.backgroundColor = mer; carte.Habiller(mer, Color.Lerp(mer, papier, .11f), papier);
                    // Au-delà d'une coupe de la carte, le papier du socle.
                    carte.PeindreHorsCarte(papier);
                    // Les traits du terrain à l'encre ; les lignes d'eau, une mer tirée vers le papier.
                    Color encre = SocleInterface.Couleur("encre"); carte.Encrer(encre, encre, encre, Color.Lerp(mer, papier, .45f));
                    ReleverLesNoms();
                }
                ModeDeCarte mode = Mode; var lecture = LectureDuMode.Lire(mode, lieuxLus, carte.Lue, guerre, lieux?.EnAlerte);
                // Valider tous les lieux avant de changer une seule couleur.
                foreach (var paire in rangsDesLieux) foreach (long rang in paire.Value) lecture.Valider(paire.Key, rang);
                Peindre(lecture);
                Recrire(lecture); peinte = lecture;
            }
            catch (Exception e)
            {
                // Le mode dont la donnée manque le dit, et la carte politique se montre à sa place : jamais les couleurs d'un mode sous la légende d'un autre.
                ecrite = null; var politique = new LectureDuMode(ModeDeCarte.Politique, null, null, guerre?.Terres, null, lieux?.EnAlerte);
                if (maisons != null) Peindre(politique);
                string raison = Indisponible(Mode, e.Message), detail = politique.Detail;
                try { Legender(raison, detail); }
                catch (ArgumentException) { Ecrire(COUPEE, raison + "\n" + detail, null); } // trop longue pour trois lignes : entière dans l'infobulle
            }
        }
        // Chaque lieu dessiné à la teinte du mode lu. Le pays servi et son liseré, sinon ceux de la puissance relevée au dessin :
        // la frontière suit le même pays que la teinte ; un lieu d'un autre pays que sa terre prend le pays et la couleur du sien.
        // En Relief, la terre se teint par son altitude, et liserés, frontières et noms des pays s'effacent, les rattachements restent.
        void Peindre(LectureDuMode lecture)
        {
            bool lus = lecture.Terres != null && guerre != null; var autres = new Dictionary<long, (string pays, Color pigment)>();
            foreach (var paire in maisons)
            {
                long cell = paire.Key; string pays = lus ? lecture.Terres.PaysDe(cell) : departs[cell];
                Color pigment = lus ? guerre.CouleurDuPays(pays) : SocleInterface.Pigment(paire.Value);
                carte.Rattacher(cell, pays, lus ? guerre.LisereDuPays(pays) : LisereDuPigment(pigment)); autres.Clear();
                if (lus)
                    foreach (var lieu in lecture.Terres.AutresPaysDe(cell)) { carte.RattacherLieu(cell, lieu.Rang, lieu.Pays, guerre.LisereDuPays(lieu.Pays)); autres[lieu.Rang] = (lieu.Pays, guerre.CouleurDuPays(lieu.Pays)); }
                foreach (long rang in rangsDesLieux[cell])
                {
                    var (duLieu, teinte) = autres.TryGetValue(rang, out var autre) ? autre : (pays, pigment);
                    carte.TeinterLieu(cell, rang, lecture.Teinte(cell, rang, duLieu, teinte));
                }
            }
            bool nu = lecture.Mode == ModeDeCarte.Relief; carte.MontrerLesPays(!nu); guerre?.MontrerLesNoms(!nu); carte.TeindreParLAltitude(nu ? ReliefDesTerres.Paliers : null);
            // Le liseré teint chaque pays de sa couleur le long de sa frontière : hors de la carte politique, il couvrirait la teinte du mode.
            carte.MontrerLesLiseres(lecture.Mode == ModeDeCarte.Politique);
        }
        // Les textes posés sur la carte (les villes, les sièges de l'atlas), cachés compris, hors ceux de la guerre : relevés à la
        // pose de la carte, puis chaque fois que les villes en posent ou en retirent.
        void ReleverLesNoms()
        {
            var police = SocleInterface.Police(titre: true); versionDesTextes = villesDeCarte != null ? villesDeCarte.VersionDesTextes : -1;
            var poses = carte.GetComponentsInChildren<TextMesh>(true).Where(n => guerre == null || !guerre.Possede(n.transform)).ToArray();
            // « Hors de la carte » reste couché sur le papier, à la taille de l'atlas, le long de sa coupure : il prend la police
            // et l'encre du socle, sans étiquette d'écran.
            noms = poses.Where(n => n.transform.parent == null || n.transform.parent.name != CarteDessinee.HORS_CARTE).OrderBy(n => n.text, StringComparer.Ordinal).ToArray();
            foreach (var nom in poses)
            {
                nom.font = police; nom.fontSize = 16;
                nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                nom.color = SocleInterface.Couleur("encre");
            }
        }
        void Recrire(LectureDuMode lecture)
        {
            string texte = lecture.Legende, detail = DetailDuMode(lecture, lieux, fleches, guerre) + (atlas?.Absence != null ? "\nNoms de l'atlas non lus : " + TexteDuMonde.Absence(atlas.Absence) : "") + (villesDeCarte?.TexteLegende != null ? "\n" + villesDeCarte.TexteLegende : "");
            var echelleDuMode = lecture.Echelle; Text mesure = echelleDuMode != null ? etiquettesDeLEchelle[0] : legende; // la toile peut changer d'échelle
            if (texte != ecrite || detail != detaillee || Mathf.Abs(mesure.preferredHeight - mesure.rectTransform.sizeDelta.y) > 1f)
            { if (echelleDuMode != null) Legender(echelleDuMode, detail); else Legender(texte, detail); ecrite = texte; detaillee = detail; }
        }

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
