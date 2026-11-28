using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;

namespace Forge.Interface
{
    // Comment un nom s'écrit : en capitales droites (un pays, sa maison), ou en italique, tel que servi et espacé (une mer, une région, un fleuve).
    public enum StyleDeNom { Capitales, Italique }

    // Un nom écrit le long de son tracé : le nom servi, ce qui en est écrit, et comment.
    public sealed class NomCourbe
    {
        public string Pays { get; } public string Texte { get; } public string Ecrit { get; } public StyleDeNom Style { get; }
        // Masqué par celui qui l'écrit (un nom plus important est déjà là) : il se cache comme un nom illisible.
        public bool Masque { get; internal set; }
        // Le tracé et la composition montrés : ceux d'origine, ou la variante qui laisse lire une capitale (`NomsCourbes.Eviter`).
        public TraceDeNom Trace { get; internal set; } public NomCompose Compose { get; internal set; }
        // Le corps des lettres en km de la carte : il suit l'étendue du territoire.
        public float Corps => Compose != null ? Compose.Corps : 0f;
        // De 0 (caché) à 1, selon la taille du nom à l'écran ; la force de son halo ; son corps à l'écran, en
        // pixels ; et la taille, en pixels, des lettres tirées de la police.
        public float Opacite { get; internal set; } public float Halo { get; internal set; } public float CorpsPx { get; internal set; } public int Taille { get; internal set; }
        public MeshRenderer Rendu { get; } public Mesh Maillage { get; }
        // La maison du pays, écrite en petit sous son nom ; nulle quand le pays n'en a pas d'autre nom que le sien.
        public NomCourbe Maison { get; internal set; }
        // Pour la ligne d'une maison ou d'une vassalité, le nom du pays qu'elle accompagne ; nul pour un nom de pays.
        public NomCourbe NomDuPays { get; internal set; }
        // La ligne de vassalité du pays, écrite en petit sous sa maison (ou sous son nom) ; nulle pour un pays sans suzerain.
        public NomCourbe Vassalite { get; internal set; }
        // La composition sur le tracé montré, avant tout agrandissement ; et de combien elle est agrandie (1 : telle quelle). Seul le nom du
        // pays du joueur, et ses lignes, s'agrandissent (`NomsCourbes.PaysDuJoueur`).
        public NomCompose Base { get; internal set; } public float Agrandissement { get; internal set; } = 1f;
        internal bool AMailler;
        internal NomCourbe(string pays, string texte, string ecrit, StyleDeNom style, TraceDeNom trace, NomCompose compose, MeshRenderer rendu, Mesh maillage)
        { Pays = pays; Texte = texte; Ecrit = ecrit; Style = style; Trace = trace; Compose = Base = compose; Rendu = rendu; Maillage = maillage; }
    }

    // Les noms des pays sur la carte, chacun couché sur le grand axe de son territoire, avec sa maison et, pour un vassal, « vassal de … » en petit dessous. Une lettre est un carré de
    // l'atlas de la police, posé à sa place sur le tracé et tourné dans le sens de l'écriture, puis drapé sur le
    // sol : une grande lettre se découpe en carreaux qui suivent le relief. Un nom est un seul maillage, dessiné
    // deux fois : le halo clair qui le détache du relief, puis l'encre. À chaque image, un nom se
    // règle sur sa taille à l'écran : trop petit pour se lire, il se cache ; quand la vue s'approche au point qu'il
    // la remplirait, il s'efface et laisse lire ce qu'il couvrait. Ses lettres sont tirées de la police à la taille la
    // plus proche de celle de l'écran, pour rester nettes de loin comme de près.
    // La police est dynamique : son atlas peut être refait à tout moment, et les lettres y changent alors de place.
    // Les noms redemandent donc leurs lettres à chaque image et se remaillent dès que l'atlas est refait.
    // Une capitale passe devant le nom d'un pays : un nom dont une lettre tomberait sur une capitale montrée se pose à côté
    // d'elle, décalé au-dessus ou au-dessous de son tracé, ou se réduit (`Eviter`), avec sa maison et sa vassalité.
    public sealed class NomsCourbes : IDisposable
    {
        public const string RACINE = "Noms des pays", SHADER = "Forge/NomDeCarte";
        // Au ras du sol : le nom est imprimé sur le terrain. Une lettre se découpe en carreaux de `CARREAU_KM` au plus,
        // jamais plus de `CARREAUX_MAX` par côté.
        public const float HAUTEUR = 0.1f, CARREAU_KM = 8f; public const int CARREAUX_MAX = 6;
        // Ce que l'encre d'un nom couvre du terrain, au plus : le relief et les teintes se lisent au travers.
        public const float FORCE = 0.85f;
        // Un nom se cache quand son corps passe sous LISIBLE_PX pixels, sur FONDU_PX pixels ; il s'efface quand son
        // corps dépasse PROCHE de la hauteur de l'écran, et a disparu à DISPARU.
        public const float LISIBLE_PX = 10f, FONDU_PX = 2.5f, PROCHE = 0.10f, DISPARU = 0.15f;
        // Le halo : son rayon en corps ; sa force sous un petit nom, qui en a le plus besoin, et sous un grand.
        public const float RAYON_DU_HALO = 0.09f, HALO_PETIT = 0.75f, HALO_GRAND = 0.3f, PETIT_PX = 16f, GRAND_PX = 64f;
        // Un nom à demi effacé ne réserve plus sa place : les noms des villes reviennent.
        public const float OPACITE_QUI_RESERVE = 0.5f;
        // La maison sous le nom : son corps au plus, en part de celui du nom, et l'écart des deux lignes, en corps du nom.
        public const float PART_DE_LA_MAISON = 0.45f, ECART_DE_LA_MAISON = 0.8f;
        // La vassalité sous la maison (ou sous le nom) : son corps au plus, en part de celui du nom, et le blanc laissé entre les deux lignes, en corps de la vassalité.
        public const float PART_DE_LA_VASSALITE = 0.32f, ECART_DE_LA_VASSALITE = 0.5f;
        // L'italique : la pente des lettres (le décalage vers l'est par corps de hauteur), et l'espace ajouté après chaque lettre, en corps.
        public const float PENTE_DE_L_ITALIQUE = 0.22f, ESPACEMENT_DE_L_ITALIQUE = 0.12f;
        // Les variantes d'un nom qui couvre une capitale : décalé en travers de son tracé par pas de `PAS_DU_DECALAGE` corps, au-dessus
        // puis au-dessous, jusqu'à `DECALAGES` pas ; puis réduit de `REDUCTION`, puis de son carré, sur un tracé raccourci d'autant posé au
        // milieu, au début ou à la fin du tracé d'origine, en place et décalé de même. `ECHELLES` : la part gardée du tracé et sa place
        // (-1 au début, 0 au milieu, 1 à la fin), la première étant le tracé d'origine.
        public const float PAS_DU_DECALAGE = 0.5f, REDUCTION = 0.6f; public const int DECALAGES = 8;
        static readonly (float part, float place)[] ECHELLES = { (1f, 0f), (REDUCTION, 0f), (REDUCTION, -1f), (REDUCTION, 1f), (REDUCTION * REDUCTION, 0f), (REDUCTION * REDUCTION, -1f), (REDUCTION * REDUCTION, 1f) };
        // Une variante garde le nom sur la terre de son pays : au plus `LETTRES_HORS_DE_SA_TERRE` de ses lettres hors d'elle, comme le
        // tracé d'origine tolère un trou. `SurSaTerre` dit si un point (km de la carte) est sur la terre d'un pays ; sans lui, toute variante l'est.
        public const int LETTRES_HORS_DE_SA_TERRE = 1;
        public Func<string, Vector2, bool> SurSaTerre { get; set; }
        // Le pays du joueur : son nom ne se cache jamais faute de taille. Quand son corps passerait sous `CORPS_DU_JOUEUR_PX` pixels, ses
        // lignes s'agrandissent autour du milieu de son tracé jusqu'à ce corps, et reviennent à leur taille dès qu'elles le dépassent ;
        // de trop près, il s'efface comme les autres. Nul : aucun nom ne s'agrandit.
        public const float CORPS_DU_JOUEUR_PX = 16f;
        public string PaysDuJoueur { get; set; }
        // La variante montrée du nom d'un pays : son échelle (son rang dans `ECHELLES`, 0 d'origine) et son décalage en travers, en km ; (0, 0) pour un nom posé à son tracé d'origine.
        public (int echelle, float decalage) VarianteDe(NomCourbe nom) { foreach (Groupe g in groupes) if (g.Lignes[0] == nom) return (g.Echelle, g.Decalage); return (0, 0f); }
        // Le corps du nom d'un pays sur son tracé d'origine, en km, quelle que soit la variante montrée.
        public float CorpsDOrigine(NomCourbe nom) { foreach (Groupe g in groupes) if (g.Lignes[0] == nom) return g.Dispositions[0][0].compose.Corps; return nom?.Corps ?? 0f; }
        // Les tailles tirées de la police, en pixels ; la mise en page se fait à la taille de référence.
        static readonly int[] TAILLES = { 12, 16, 24, 32, 48, 64, 96, 128 }; const int REFERENCE = 64;
        const string CAPITALE = "H"; const float HAUTEUR_DE_CAPITALE = 0.7f, AVANCE_INCONNUE = 0.5f; const int ESSAIS = 4;

        readonly Transform racine; readonly Font police; readonly Material encre, halo; readonly Material[] matieres; readonly bool matieresCreees;
        // `noms` : les noms des pays ; `lignes` : tout ce qui s'écrit, chaque nom suivi de sa maison.
        readonly List<NomCourbe> noms = new List<NomCourbe>(), lignes = new List<NomCourbe>(); bool refait; readonly Color32 deSecours; readonly Func<Vector2, Vector3> sol;
        readonly List<Groupe> groupes = new List<Groupe>();
        // Les lignes d'un pays (son nom, sa maison, sa vassalité) et ce que leurs lettres avancent ; leur disposition sur le tracé
        // d'origine et sur chaque tracé réduit de `ECHELLES` (nulle s'il ne s'y compose pas), avec le milieu et le rayon de leurs lettres,
        // en km ; puis la variante montrée : son échelle (son rang dans `ECHELLES`, 0 d'origine) et son décalage en travers, en km vers le
        // haut des lettres.
        sealed class Groupe
        {
            public float[][] Avances; public bool AMaison, AVassal; public NomCourbe[] Lignes; public TraceDeNom Trace;
            public readonly (TraceDeNom trace, NomCompose compose)[][] Dispositions = new (TraceDeNom, NomCompose)[ECHELLES.Length][];
            public readonly Vector2[] Milieux = new Vector2[ECHELLES.Length]; public readonly float[] Rayons = new float[ECHELLES.Length];
            public int Echelle; public float Decalage;
        }
        // Les lettres à demander à la police pour chaque taille, et ce dont elles ont été tirées : refaites seulement quand les noms montrés à cette taille changent.
        readonly string[] demandes = new string[TAILLES.Length]; readonly long[] signatures = new long[TAILLES.Length];

        public IReadOnlyList<NomCourbe> Noms => noms;
        public Font Police => police;
        public Transform Racine => racine;
        // Les deux matériaux d'un nom : celui de son encre, et celui de son halo (nul faute du shader des noms).
        public Material Encre => encre;
        public Material MatiereDuHalo => halo;

        // `sol` rend, pour un point (x, z) de la carte, sa place sur le sol, en local ; sans lui, les noms sont à plat.
        public NomsCourbes(Transform parent, Font police, Color teinteDeLEncre, Color teinteDuHalo, Func<Vector2, Vector3> sol = null)
        {
            this.police = police != null ? police : throw new ArgumentNullException(nameof(police)); this.sol = sol;
            racine = new GameObject(RACINE).transform; racine.SetParent(parent, false);
            Shader shader = Resources.Load<Shader>(SHADER); deSecours = teinteDeLEncre;
            if (shader != null)
            {
                teinteDeLEncre.a = FORCE; teinteDuHalo.a = 1f;
                halo = new Material(shader) { name = RACINE + " (halo)", mainTexture = police.material.mainTexture }; halo.SetColor("_Teinte", teinteDuHalo); halo.SetFloat("_Halo", 1f);
                encre = new Material(shader) { name = RACINE + " (encre)", mainTexture = police.material.mainTexture }; encre.SetColor("_Teinte", teinteDeLEncre); encre.SetFloat("_Halo", 0f);
                encre.renderQueue = shader.renderQueue; halo.renderQueue = encre.renderQueue - 1; matieres = new[] { halo, encre }; matieresCreees = true;
            }
            else { encre = police.material; matieres = new[] { encre }; } // faute du shader des noms, celui de la police : sans halo, et devant tout
            Font.textureRebuilt += AtlasRefait;
        }

        public void Dispose()
        {
            Font.textureRebuilt -= AtlasRefait; Vider();
            if (matieresCreees) { Detruire(encre); Detruire(halo); }
            if (racine != null) Detruire(racine.gameObject);
        }

        // De 0 à 1 : ce qu'un nom montre de son encre quand son corps fait `corpsPx` pixels sur un écran de `ecranPx` de haut.
        public static float Opacite(float corpsPx, float ecranPx)
        {
            if (ecranPx <= 0f) return 0f;
            return Lisse(LISIBLE_PX - FONDU_PX, LISIBLE_PX, corpsPx) * (1f - Lisse(PROCHE * ecranPx, DISPARU * ecranPx, corpsPx));
        }
        // La force du halo d'un nom de ce corps à l'écran : forte sous un petit nom, légère sous un grand.
        public static float ForceDuHalo(float corpsPx) => Mathf.Lerp(HALO_PETIT, HALO_GRAND, Mathf.InverseLerp(PETIT_PX, GRAND_PX, corpsPx));
        static float Lisse(float de, float a, float x) { float t = Mathf.Clamp01((x - de) / (a - de)); return t * t * (3f - 2f * t); }
        // La plus petite taille tirée de la police qui ne s'agrandit pas à l'écran ; la plus grande au-delà.
        public static int TaillePour(float corpsPx) { foreach (int taille in TAILLES) if (taille >= corpsPx) return taille; return TAILLES[TAILLES.Length - 1]; }

        // Le corps d'un nom à l'écran, en pixels, là où il est écrit : le km de la carte y est mesuré dans le sens
        // de l'écriture et en travers, et le plus grand des deux est gardé.
        public float CorpsALEcran(Camera camera, NomCourbe nom)
        {
            if (camera == null || nom.Compose == null) return 0f;
            float milieu = (nom.Trace.Debut + nom.Trace.Fin) / 2f; Vector2 p = nom.Trace.Point(milieu), sens = nom.Trace.Sens(milieu), haut = new Vector2(-sens.y, sens.x);
            Vector2 ici = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p)));
            Vector2 enLong = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p + sens)));
            Vector2 enTravers = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p + haut)));
            return nom.Corps * Mathf.Max((enLong - ici).magnitude, (enTravers - ici).magnitude);
        }

        // La place que chaque lettre d'un nom lisible tient à l'écran, ajoutée à `places` : un nom de ville ne s'écrit pas dessus.
        public void Reserver(Camera camera, List<Rect> places)
        {
            if (camera == null) return;
            foreach (NomCourbe nom in lignes) if (nom.Opacite >= OPACITE_QUI_RESERVE) Places(camera, nom, places);
        }
        // La place de chaque lettre d'un nom à l'écran, à son corps de la dernière image, qu'il soit montré ou non ; seules celles qui sont dans l'écran.
        public void Places(Camera camera, NomCourbe nom, List<Rect> places)
        {
            if (camera == null || nom?.Compose == null) return;
            Rect ecran = camera.pixelRect; float demi = nom.CorpsPx * 0.45f;
            for (int i = 0; i < nom.Ecrit.Length; i++)
            {
                if (char.IsWhiteSpace(nom.Ecrit[i])) continue;
                Vector3 p = camera.WorldToScreenPoint(racine.TransformPoint(Poser(nom.Compose.Lettres[i].Point)));
                var place = new Rect(p.x - demi, p.y - demi, 2f * demi, 2f * demi);
                if (p.z > 0f && place.Overlaps(ecran)) places.Add(place);
            }
        }
        public IReadOnlyList<NomCourbe> Lignes => lignes;

        // Écrit un nom par pays tracé, à la place de ceux d'avant. Un pays dont le tracé ne laisse rien écrire n'a pas de nom.
        public void Ecrire(IEnumerable<(string pays, string nom, TraceDeNom trace)> pays) => Ecrire(pays.Select(p => (p.pays, p.nom, (string)null, p.trace)));

        // Avec sa maison : quand elle porte un autre nom que le pays, elle s'écrit en petit sous lui, sur le même arc descendu
        // d'environ un corps. Un pays qui est sa propre maison (un seigneur libre) n'a qu'une ligne.
        public void Ecrire(IEnumerable<(string pays, string nom, string maison, TraceDeNom trace)> pays) => Ecrire(pays.Select(p => (p.pays, p.nom, p.maison, (string)null, p.trace)));

        // Avec son suzerain, nom servi ou nul : un vassal écrit une ligne de plus, en petit italique, sous sa maison ou, sans maison, sous son nom.
        public void Ecrire(IEnumerable<(string pays, string nom, string maison, string suzerain, TraceDeNom trace)> pays)
        {
            Vider(); for (int t = 0; t < TAILLES.Length; t++) { demandes[t] = null; signatures[t] = 0; }
            foreach (var (id, texte, maison, suzerain, trace) in pays)
            {
                if (trace == null || string.IsNullOrEmpty(texte)) continue;
                var textes = new List<(string objet, string texte, StyleDeNom style)> { ("Pays " + id, texte, StyleDeNom.Capitales) };
                bool aMaison = !string.IsNullOrWhiteSpace(maison) && !string.Equals(maison.Trim(), texte.Trim(), StringComparison.OrdinalIgnoreCase);
                if (aMaison) textes.Add(("Maison du pays " + id, maison, StyleDeNom.Capitales));
                string vassal = Vassalite(suzerain); if (vassal != null) textes.Add(("Vassalité du pays " + id, vassal, StyleDeNom.Italique));
                var g = new Groupe { Avances = textes.Select(t => Avances(Ecrit(t.texte, t.style), t.style)).ToArray(), AMaison = aMaison, AVassal = vassal != null, Trace = trace };
                var disposition = Disposer(trace, g); if (disposition == null) continue;
                g.Lignes = textes.Select((t, k) => Poser(t.objet, id, t.texte, t.style, disposition[k].trace, disposition[k].compose)).ToArray();
                NomCourbe nom = g.Lignes[0]; noms.Add(nom); lignes.AddRange(g.Lignes);
                for (int k = 1; k < g.Lignes.Length; k++) g.Lignes[k].NomDuPays = nom;
                if (aMaison) nom.Maison = g.Lignes[1]; if (vassal != null) nom.Vassalite = g.Lignes[g.Lignes.Length - 1];
                g.Dispositions[0] = disposition; for (int e = 1; e < ECHELLES.Length; e++) g.Dispositions[e] = Disposer(Reduire(trace, ECHELLES[e].part, ECHELLES[e].place), g);
                for (int e = 0; e < ECHELLES.Length; e++) if (g.Dispositions[e] != null) (g.Milieux[e], g.Rayons[e]) = Etendue(g.Dispositions[e]);
                groupes.Add(g);
            }
        }

        // Les lignes d'un pays sur un tracé : son nom ; sa maison en petit sous lui, sur le même arc descendu d'environ un corps ; sa
        // vassalité sous la ligne du dessus, d'une demi-ligne de chacune et d'un blanc. Null si une ligne ne s'y compose pas.
        static (TraceDeNom trace, NomCompose compose)[] Disposer(TraceDeNom trace, Groupe g)
        {
            var lignes = new (TraceDeNom, NomCompose)[g.Avances.Length]; NomCompose nom = trace.Composer(g.Avances[0]); if (nom == null) return null;
            lignes[0] = (trace, nom); NomCompose dessus = nom; float ecart = nom.Corps * ECART_DE_LA_MAISON; int k = 1;
            if (g.AMaison)
            {
                TraceDeNom sous = trace.Dessous(ecart, nom.Corps * PART_DE_LA_MAISON / TraceDeNom.PART_DE_LA_LARGEUR); NomCompose maison = sous.Composer(g.Avances[k]); if (maison == null) return null;
                lignes[k++] = (sous, maison); dessus = maison;
            }
            if (g.AVassal)
            {
                float petit = nom.Corps * PART_DE_LA_VASSALITE, descente = (dessus == nom ? 0f : ecart) + dessus.Corps / 2f + petit * (0.5f + ECART_DE_LA_VASSALITE);
                TraceDeNom sous = trace.Dessous(descente, petit / TraceDeNom.PART_DE_LA_LARGEUR); NomCompose vassalite = sous.Composer(g.Avances[k]); if (vassalite == null) return null;
                lignes[k] = (sous, vassalite);
            }
            return lignes;
        }
        // Le même arc, raccourci et rétréci à `part` de lui-même, posé à son milieu, à son début (`place` -1) ou à sa fin (1) : un nom plus petit.
        static TraceDeNom Reduire(TraceDeNom t, float part, float place)
        {
            const float S = 100f; float a = Vector2.Dot(t.Point(0f) - t.Centre, t.Travers), b = (Vector2.Dot(t.Point(S) - t.Centre - t.Axe * S, t.Travers) - a - t.Courbure * S * S) / S;
            float demiOrigine = (t.Fin - t.Debut) / 2f, demi = demiOrigine * part, milieu = (t.Debut + t.Fin) / 2f + place * (demiOrigine - demi);
            return new TraceDeNom(t.Centre, t.Axe, milieu - demi, milieu + demi, a, b, t.Courbure, t.Largeur * part, t.Echantillons);
        }
        // Le milieu des lettres d'une disposition et le rayon qui les contient toutes, lettres comprises, en km.
        static (Vector2, float) Etendue((TraceDeNom trace, NomCompose compose)[] disposition)
        {
            var points = disposition.SelectMany(l => l.compose.Lettres.Select(p => p.Point)).ToList(); Vector2 milieu = Vector2.zero; foreach (Vector2 p in points) milieu += p; milieu /= points.Count;
            return (milieu, points.Max(p => (p - milieu).magnitude) + disposition[0].compose.Corps);
        }

        // Pose chaque nom de pays sur la première de ses variantes dont aucune lettre qui se montrerait ne tombe sur une des `places`
        // (en pixels de l'écran : les capitales montrées) : le tracé d'origine d'abord, puis décalé au plus près, au-dessus puis au-dessous,
        // puis réduit, s'il se lit encore. Le tracé d'origine quand aucune ne les évite, ou quand le nom ne se montre pas. Les variantes
        // se jugent au corps des lettres de la dernière image ; seul un nom qui change de variante se recompose et se remaille.
        public void Eviter(Camera camera, IReadOnlyList<Rect> places)
        {
            if (camera == null) return;
            foreach (Groupe g in groupes)
            {
                var (echelle, decalage) = Choisir(camera, g, places);
                if (echelle == g.Echelle && decalage == g.Decalage) continue;
                g.Echelle = echelle; g.Decalage = decalage;
                for (int k = 0; k < g.Lignes.Length; k++)
                {
                    var (trace, compose) = g.Dispositions[echelle][k];
                    if (decalage != 0f) { TraceDeNom decale = trace.Dessous(-decalage, trace.Largeur); NomCompose recompose = decale.Composer(g.Avances[k]); if (recompose != null) (trace, compose) = (decale, recompose); }
                    NomCourbe ligne = g.Lignes[k]; ligne.Trace = trace; ligne.Compose = ligne.Base = compose; ligne.Agrandissement = 1f; ligne.AMailler = true;
                }
            }
        }
        (int, float) Choisir(Camera camera, Groupe g, IReadOnlyList<Rect> places)
        {
            if (places == null || places.Count == 0 || g.Lignes[0].Opacite <= 0f || Libre(camera, g, 0, 0f, places)) return (0, 0f);
            for (int e = 0; e < ECHELLES.Length; e++)
            {
                if (g.Dispositions[e] == null || (e > 0 && Px(g, e, 0) < LISIBLE_PX)) continue;
                float pas = PAS_DU_DECALAGE * g.Dispositions[e][0].compose.Corps;
                for (int k = e == 0 ? 1 : 0; k <= DECALAGES; k++)
                {
                    if (SurLaTerre(g, e, k * pas) && Libre(camera, g, e, k * pas, places)) return (e, k * pas);
                    if (k > 0 && SurLaTerre(g, e, -k * pas) && Libre(camera, g, e, -k * pas, places)) return (e, -k * pas);
                }
            }
            return (0, 0f);
        }
        // Les lettres du nom de cette variante sont sur la terre de son pays, à `LETTRES_HORS_DE_SA_TERRE` près.
        bool SurLaTerre(Groupe g, int echelle, float decalage)
        {
            if (SurSaTerre == null) return true;
            NomCourbe nom = g.Lignes[0]; var lettres = g.Dispositions[echelle][0].compose.Lettres; Vector2 enTravers = g.Trace.Travers * decalage; int dehors = 0;
            for (int i = 0; i < nom.Ecrit.Length; i++) if (!char.IsWhiteSpace(nom.Ecrit[i]) && !SurSaTerre(nom.Pays, lettres[i].Point + enTravers) && ++dehors > LETTRES_HORS_DE_SA_TERRE) return false;
            return true;
        }
        // Le corps à l'écran qu'aurait cette ligne dans cette échelle, d'après celui de la dernière image.
        static float Px(Groupe g, int echelle, int ligne) { NomCourbe l = g.Lignes[ligne]; return l.Corps > 0f ? l.CorpsPx * g.Dispositions[echelle][ligne].compose.Corps / l.Corps : 0f; }
        // Aucune lettre de cette variante qui se montrerait ne tombe sur une des places. Loin de toutes, le groupe ne se lit pas lettre à lettre.
        bool Libre(Camera camera, Groupe g, int echelle, float decalage, IReadOnlyList<Rect> places)
        {
            var disposition = g.Dispositions[echelle]; Vector2 enTravers = g.Trace.Travers * decalage; float ecran = camera.pixelHeight;
            NomCourbe nom = g.Lignes[0]; float parKm = nom.Corps > 0f ? nom.CorpsPx / nom.Corps : 0f;
            Vector3 milieu = camera.WorldToScreenPoint(racine.TransformPoint(Poser(g.Milieux[echelle] + enTravers))); float rayon = g.Rayons[echelle] * parKm + nom.CorpsPx;
            var boite = new Rect(milieu.x - rayon, milieu.y - rayon, 2f * rayon, 2f * rayon); bool proche = false;
            foreach (Rect place in places) if (place.Overlaps(boite)) { proche = true; break; }
            if (!proche) return true;
            for (int k = 0; k < disposition.Length; k++)
            {
                float px = Px(g, echelle, k); if (Opacite(px, ecran) <= 0f) continue;
                float demi = px * 0.45f; string ecrit = g.Lignes[k].Ecrit; var lettres = disposition[k].compose.Lettres;
                for (int i = 0; i < ecrit.Length; i++)
                {
                    if (char.IsWhiteSpace(ecrit[i])) continue;
                    Vector3 p = camera.WorldToScreenPoint(racine.TransformPoint(Poser(lettres[i].Point + enTravers))); if (p.z <= 0f) continue;
                    var lettre = new Rect(p.x - demi, p.y - demi, 2f * demi, 2f * demi);
                    foreach (Rect place in places) if (place.Overlaps(lettre)) return false;
                }
            }
            return true;
        }

        // « vassal de France », « vassal d'Angleterre » : le texte de la ligne d'un vassal, élidé devant une voyelle (accentuée ou non) et jamais
        // devant un h, aspiré dans Hongrie, Hainaut ou Hesse ; nul sans nom de suzerain.
        public static string Vassalite(string suzerain)
        {
            if (string.IsNullOrWhiteSpace(suzerain)) return null;
            string nom = suzerain.Trim(); char initiale = char.ToLowerInvariant(nom.Normalize(NormalizationForm.FormD)[0]);
            return (VOYELLES.IndexOf(initiale) >= 0 ? "vassal d'" : "vassal de ") + nom;
        }
        const string VOYELLES = "aeiouy";

        // Écrit des noms à plat, chacun droit sur son axe, centré sur son point, à un corps donné en km, dans son style : les
        // noms d'un atlas. Un nom de corps nul ou sans texte n'est pas écrit.
        public void Ecrire(IEnumerable<(string id, string texte, Vector2 centre, Vector2 axe, float corps, StyleDeNom style)> aPlat)
        {
            Vider(); for (int t = 0; t < TAILLES.Length; t++) { demandes[t] = null; signatures[t] = 0; }
            foreach (var (id, texte, centre, axe, corps, style) in aPlat)
            {
                if (string.IsNullOrEmpty(texte) || !(corps > 0f)) continue;
                float[] avances = Avances(Ecrit(texte, style), style); float naturel = avances.Sum();
                // Un tracé droit juste assez long et assez large pour que le nom y tienne à ce corps, et pas plus grand.
                float longueur = corps * naturel / TraceDeNom.PART_DE_LA_LONGUEUR * 1.0001f, largeur = corps / TraceDeNom.PART_DE_LA_LARGEUR * 1.0001f;
                Vector2 sens = axe.sqrMagnitude > 0f ? axe.normalized : Vector2.right; if (sens.x < 0f) sens = -sens;
                NomCourbe nom = Poser("Nom " + id, id, texte, style, new TraceDeNom(centre, sens, -longueur / 2f, longueur / 2f, 0f, 0f, 0f, largeur, 1));
                if (nom != null) { noms.Add(nom); lignes.Add(nom); }
            }
        }

        static string Ecrit(string texte, StyleDeNom style) => style == StyleDeNom.Capitales ? texte.ToUpperInvariant() : texte;
        // Ce que chaque lettre avance, en corps ; l'italique s'espace.
        float[] Avances(string ecrit, StyleDeNom style)
        {
            Demander(ecrit, REFERENCE); var avances = new float[ecrit.Length];
            for (int i = 0; i < ecrit.Length; i++)
                avances[i] = (police.GetCharacterInfo(ecrit[i], out CharacterInfo lettre, REFERENCE) ? lettre.advance / (float)REFERENCE : AVANCE_INCONNUE) + (style == StyleDeNom.Italique ? ESPACEMENT_DE_L_ITALIQUE : 0f);
            return avances;
        }

        // Compose un texte sur son tracé et pose son maillage, encore vide ; null s'il n'y a rien à écrire.
        NomCourbe Poser(string objetNomme, string id, string texte, StyleDeNom style, TraceDeNom trace)
        {
            if (trace == null || string.IsNullOrEmpty(texte)) return null;
            NomCompose compose = trace.Composer(Avances(Ecrit(texte, style), style));
            return compose == null ? null : Poser(objetNomme, id, texte, style, trace, compose);
        }
        NomCourbe Poser(string objetNomme, string id, string texte, StyleDeNom style, TraceDeNom trace, NomCompose compose)
        {
            string ecrit = Ecrit(texte, style);
            var objet = new GameObject(objetNomme, typeof(MeshFilter), typeof(MeshRenderer)); objet.transform.SetParent(racine, false);
            var maillage = new Mesh { name = "Nom de " + id }; maillage.MarkDynamic(); objet.GetComponent<MeshFilter>().sharedMesh = maillage;
            var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterials = matieres; rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false; rendu.enabled = false;
            return new NomCourbe(id, texte, ecrit, style, trace, compose, rendu, maillage);
        }

        // Règle chaque nom sur la vue : son opacité, son halo, la taille de ses lettres, et son maillage quand il le
        // faut ou que l'atlas a été refait. La maison suit la règle du nom à son propre corps, et jamais plus que lui :
        // elle se cache plus tôt de loin, et s'efface avec lui de près. La vassalité fait de même, et jamais plus que la maison.
        public void Suivre(Camera camera)
        {
            if (camera == null || noms.Count == 0) return;
            Agrandir(camera);
            float ecran = camera.pixelHeight;
            foreach (NomCourbe nom in lignes)
            {
                float px = CorpsALEcran(camera, nom), opacite = Opacite(px, ecran), force = ForceDuHalo(px); nom.CorpsPx = px;
                if (nom.NomDuPays != null)
                {
                    opacite = Mathf.Min(opacite, nom.NomDuPays.Opacite);
                    if (nom.NomDuPays.Vassalite == nom && nom.NomDuPays.Maison != null) opacite = Mathf.Min(opacite, nom.NomDuPays.Maison.Opacite);
                }
                if (nom.Masque) opacite = 0f;
                if (opacite > 0f) { int taille = TaillePour(px); if (taille != nom.Taille) { nom.Taille = taille; nom.AMailler = true; } }
                if (Mathf.Abs(opacite - nom.Opacite) > 1f / 512f || (opacite == 0f) != (nom.Opacite == 0f) || Mathf.Abs(force - nom.Halo) > 1f / 128f)
                { nom.Opacite = opacite; nom.Halo = force; if (!nom.AMailler) Teinter(nom); }
                nom.Rendu.enabled = opacite > 0f;
            }
            // Les lettres montrées restent dans l'atlas tant qu'elles sont demandées ; une demande peut le refaire, et
            // tout se redemande alors.
            for (int essai = 0; essai < ESSAIS; essai++)
            {
                bool avant = refait; refait = false;
                for (int t = 0; t < TAILLES.Length; t++)
                {
                    // Quels noms sont montrés à cette taille : leur rang, pesé, fait une signature.
                    long signature = 0; for (int k = 0; k < lignes.Count; k++) if (lignes[k].Opacite > 0f && lignes[k].Taille == TAILLES[t]) signature = signature * 31 + k + 1;
                    if (signature != signatures[t] || (signature != 0 && demandes[t] == null))
                    {
                        signatures[t] = signature; var lettres = new StringBuilder();
                        foreach (NomCourbe nom in lignes) if (nom.Opacite > 0f && nom.Taille == TAILLES[t]) lettres.Append(nom.Ecrit);
                        demandes[t] = lettres.Length > 0 ? lettres.Append(CAPITALE).ToString() : null;
                    }
                    if (demandes[t] != null) police.RequestCharactersInTexture(demandes[t], TAILLES[t]);
                }
                if (!refait) { refait = avant; break; }
            }
            if (refait) { refait = false; Atlas(); foreach (NomCourbe nom in lignes) nom.AMailler = true; }
            foreach (NomCourbe nom in lignes) if (nom.AMailler && nom.Opacite > 0f) Mailler(nom);
        }

        // Le nom du pays du joueur, s'il est trop petit pour se lire, et ses lignes : chacune agrandie du même facteur autour du milieu du
        // tracé de son nom, pour que le nom tienne `CORPS_DU_JOUEUR_PX` pixels ; telles quelles au-delà. Un nom qui change de facteur se remaille.
        void Agrandir(Camera camera)
        {
            foreach (Groupe g in groupes)
            {
                NomCourbe nom = g.Lignes[0]; float facteur = 1f;
                if (PaysDuJoueur != null && nom.Pays == PaysDuJoueur && nom.Base != null)
                {
                    float px = nom.Base.Corps * PxParKm(camera, nom.Trace);
                    if (px > 0f && px < CORPS_DU_JOUEUR_PX) facteur = CORPS_DU_JOUEUR_PX / px;
                }
                if (Mathf.Abs(facteur - nom.Agrandissement) <= 1e-3f * facteur) continue;
                Vector2 milieu = nom.Trace.Point((nom.Trace.Debut + nom.Trace.Fin) / 2f);
                foreach (NomCourbe ligne in g.Lignes) { ligne.Compose = facteur == 1f ? ligne.Base : Agrandie(ligne.Base, facteur, milieu); ligne.Agrandissement = facteur; ligne.AMailler = true; }
            }
        }
        // Une composition agrandie de `facteur` autour de `milieu` : ses lettres écartées d'autant, leur corps grandi d'autant, leur sens gardé.
        static NomCompose Agrandie(NomCompose compose, float facteur, Vector2 milieu)
        {
            var lettres = new PlaceDeLettre[compose.Lettres.Count];
            for (int i = 0; i < lettres.Length; i++) { PlaceDeLettre l = compose.Lettres[i]; lettres[i] = new PlaceDeLettre(milieu + (l.Point - milieu) * facteur, l.Sens); }
            return new NomCompose(compose.Corps * facteur, compose.Interlettre * facteur, compose.Etendue * facteur, lettres);
        }
        // Ce que vaut un km de la carte à l'écran, en pixels, au milieu d'un tracé : mesuré dans le sens de l'écriture et en travers, le plus grand des deux.
        float PxParKm(Camera camera, TraceDeNom trace)
        {
            float milieu = (trace.Debut + trace.Fin) / 2f; Vector2 p = trace.Point(milieu), sens = trace.Sens(milieu), haut = new Vector2(-sens.y, sens.x);
            Vector3 ici = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p)));
            if (ici.z <= 0f) return 0f;
            Vector2 enLong = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p + sens))), enTravers = camera.WorldToScreenPoint(racine.TransformPoint(Poser(p + haut)));
            return Mathf.Max((enLong - (Vector2)ici).magnitude, (enTravers - (Vector2)ici).magnitude);
        }

        void Demander(string lettres, int taille) => police.RequestCharactersInTexture(lettres + CAPITALE, taille);
        void Atlas() { if (!matieresCreees) return; encre.mainTexture = police.material.mainTexture; halo.mainTexture = police.material.mainTexture; }

        // L'atlas vient d'être refait : les noms montrés se remaillent tout de suite, sans rien demander à la police,
        // et tout sera redemandé à la prochaine image.
        void AtlasRefait(Font changee)
        {
            if (changee != police) return;
            refait = true; Atlas();
            foreach (NomCourbe nom in lignes) if (nom.Opacite > 0f && nom.Taille > 0) Mailler(nom);
        }

        // Un carré par lettre, à sa place sur le tracé ; les capitales sont centrées en hauteur sur la ligne du tracé.
        // Le carré déborde du dessin de la lettre de la marge du halo, et son cadre dit où la lettre finit dans l'atlas.
        void Mailler(NomCourbe nom)
        {
            int taille = nom.Taille; float echelle = nom.Corps / taille, rayon = RAYON_DU_HALO * taille, marge = Mathf.Ceil(rayon) + 1f;
            float capitale = police.GetCharacterInfo(CAPITALE[0], out CharacterInfo h, taille) && h.maxY > 0 ? h.maxY : HAUTEUR_DE_CAPITALE * taille;
            float pente = nom.Style == StyleDeNom.Italique ? PENTE_DE_L_ITALIQUE : 0f, espace = nom.Style == StyleDeNom.Italique ? ESPACEMENT_DE_L_ITALIQUE * taille : 0f;
            int n = nom.Ecrit.Length; var sommets = new List<Vector3>(4 * n); var uv = new List<Vector2>(4 * n); var cadres = new List<Vector4>(4 * n); var rayons = new List<Vector2>(4 * n); var triangles = new List<int>(6 * n);
            bool complet = true;
            for (int i = 0; i < n; i++)
            {
                if (char.IsWhiteSpace(nom.Ecrit[i])) continue;
                if (!police.GetCharacterInfo(nom.Ecrit[i], out CharacterInfo lettre, taille)) { complet = false; continue; }
                if (lettre.glyphWidth == 0 || lettre.glyphHeight == 0) continue;
                PlaceDeLettre place = nom.Compose.Lettres[i]; Vector2 sens = place.Sens, haut = place.Haut; int premier = sommets.Count;
                // Dans l'atlas, ce que vaut un pixel de la lettre vers sa droite et vers son haut : une lettre peut y être couchée.
                Vector2 bas = lettre.uvBottomLeft, versLaDroite = (lettre.uvBottomRight - bas) / (lettre.maxX - lettre.minX), versLeHaut = (lettre.uvTopLeft - bas) / (lettre.maxY - lettre.minY);
                Vector2 coin = lettre.uvTopRight; var cadre = new Vector4(Mathf.Min(bas.x, coin.x), Mathf.Min(bas.y, coin.y), Mathf.Max(bas.x, coin.x), Mathf.Max(bas.y, coin.y));
                float x0 = lettre.minX - marge, x1 = lettre.maxX + marge, y0 = lettre.minY - marge, y1 = lettre.maxY + marge;
                int carreaux = Mathf.Clamp(Mathf.CeilToInt(Mathf.Max(x1 - x0, y1 - y0) * echelle / CARREAU_KM), 1, CARREAUX_MAX), cote = carreaux + 1;
                for (int ligne = 0; ligne < cote; ligne++)
                    for (int colonne = 0; colonne < cote; colonne++)
                    {
                        float x = Mathf.Lerp(x0, x1, colonne / (float)carreaux), y = Mathf.Lerp(y0, y1, ligne / (float)carreaux);
                        sommets.Add(Poser(place.Point + sens * ((x - (lettre.advance + espace) / 2f + pente * (y - capitale / 2f)) * echelle) + haut * ((y - capitale / 2f) * echelle)));
                        uv.Add(bas + versLaDroite * (x - lettre.minX) + versLeHaut * (y - lettre.minY)); cadres.Add(cadre); rayons.Add(new Vector2(rayon, 0f));
                    }
                for (int ligne = 0; ligne < carreaux; ligne++)
                    for (int colonne = 0; colonne < carreaux; colonne++)
                    {
                        int a = premier + ligne * cote + colonne, b = a + 1, c = a + cote, d = c + 1;
                        triangles.Add(a); triangles.Add(d); triangles.Add(b); triangles.Add(a); triangles.Add(c); triangles.Add(d);
                    }
            }
            Mesh m = nom.Maillage; m.Clear(); m.SetVertices(sommets); m.SetUVs(0, uv); m.SetUVs(1, cadres); m.SetUVs(2, rayons);
            m.subMeshCount = matieres.Length; for (int s = 0; s < matieres.Length; s++) m.SetTriangles(triangles, s);
            m.RecalculateBounds(); nom.AMailler = !complet; Teinter(nom);
        }
        Vector3 Poser(Vector2 p) => sol != null ? sol(p) : new Vector3(p.x, HAUTEUR, p.y);

        // Par sommet : l'opacité du nom (alpha) et la force de son halo (rouge) ; sous le shader de la police, la teinte de l'encre.
        void Teinter(NomCourbe nom)
        {
            var teinte = new Color32((byte)Mathf.RoundToInt(255f * nom.Halo), 0, 0, (byte)Mathf.RoundToInt(255f * nom.Opacite));
            if (!matieresCreees) { teinte = deSecours; teinte.a = (byte)Mathf.RoundToInt(255f * FORCE * nom.Opacite); }
            var teintes = new Color32[nom.Maillage.vertexCount]; for (int k = 0; k < teintes.Length; k++) teintes[k] = teinte;
            nom.Maillage.colors32 = teintes;
        }

        void Vider()
        {
            foreach (NomCourbe nom in lignes) { Detruire(nom.Maillage); if (nom.Rendu != null) Detruire(nom.Rendu.gameObject); }
            noms.Clear(); lignes.Clear(); groupes.Clear();
        }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(o); else UnityEngine.Object.DestroyImmediate(o); }
    }
}
