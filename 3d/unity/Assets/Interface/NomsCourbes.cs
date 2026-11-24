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
        public TraceDeNom Trace { get; } public NomCompose Compose { get; }
        // Le corps des lettres en km de la carte : il suit l'étendue du territoire.
        public float Corps => Compose != null ? Compose.Corps : 0f;
        // De 0 (caché) à 1, selon la taille du nom à l'écran ; la force de son halo ; son corps à l'écran, en
        // pixels ; et la taille, en pixels, des lettres tirées de la police.
        public float Opacite { get; internal set; } public float Halo { get; internal set; } public float CorpsPx { get; internal set; } public int Taille { get; internal set; }
        public MeshRenderer Rendu { get; } public Mesh Maillage { get; }
        // La maison du pays, écrite en petit sous son nom ; nulle quand le pays n'en a pas d'autre nom que le sien.
        public NomCourbe Maison { get; internal set; }
        // Pour la ligne d'une maison, le nom du pays qu'elle accompagne ; nul pour un nom de pays.
        public NomCourbe NomDuPays { get; internal set; }
        internal bool AMailler;
        internal NomCourbe(string pays, string texte, string ecrit, StyleDeNom style, TraceDeNom trace, NomCompose compose, MeshRenderer rendu, Mesh maillage)
        { Pays = pays; Texte = texte; Ecrit = ecrit; Style = style; Trace = trace; Compose = compose; Rendu = rendu; Maillage = maillage; }
    }

    // Les noms des pays sur la carte, chacun couché sur le grand axe de son territoire. Une lettre est un carré de
    // l'atlas de la police, posé à sa place sur le tracé et tourné dans le sens de l'écriture, puis drapé sur le
    // sol : une grande lettre se découpe en carreaux qui suivent le relief. Un nom est un seul maillage, dessiné
    // deux fois : le halo clair qui le détache du relief, puis l'encre. À chaque image, un nom se
    // règle sur sa taille à l'écran : trop petit pour se lire, il se cache ; quand la vue s'approche au point qu'il
    // la remplirait, il s'efface et laisse lire ce qu'il couvrait. Ses lettres sont tirées de la police à la taille la
    // plus proche de celle de l'écran, pour rester nettes de loin comme de près.
    // La police est dynamique : son atlas peut être refait à tout moment, et les lettres y changent alors de place.
    // Les noms redemandent donc leurs lettres à chaque image et se remaillent dès que l'atlas est refait.
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
        // L'italique : la pente des lettres (le décalage vers l'est par corps de hauteur), et l'espace ajouté après chaque lettre, en corps.
        public const float PENTE_DE_L_ITALIQUE = 0.22f, ESPACEMENT_DE_L_ITALIQUE = 0.12f;
        // Les tailles tirées de la police, en pixels ; la mise en page se fait à la taille de référence.
        static readonly int[] TAILLES = { 12, 16, 24, 32, 48, 64, 96, 128 }; const int REFERENCE = 64;
        const string CAPITALE = "H"; const float HAUTEUR_DE_CAPITALE = 0.7f, AVANCE_INCONNUE = 0.5f; const int ESSAIS = 4;

        readonly Transform racine; readonly Font police; readonly Material encre, halo; readonly Material[] matieres; readonly bool matieresCreees;
        // `noms` : les noms des pays ; `lignes` : tout ce qui s'écrit, chaque nom suivi de sa maison.
        readonly List<NomCourbe> noms = new List<NomCourbe>(), lignes = new List<NomCourbe>(); bool refait; readonly Color32 deSecours; readonly Func<Vector2, Vector3> sol;
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
        public void Ecrire(IEnumerable<(string pays, string nom, string maison, TraceDeNom trace)> pays)
        {
            Vider(); for (int t = 0; t < TAILLES.Length; t++) { demandes[t] = null; signatures[t] = 0; }
            foreach (var (id, texte, maison, trace) in pays)
            {
                NomCourbe nom = Poser("Pays " + id, id, texte, StyleDeNom.Capitales, trace);
                if (nom == null) continue;
                noms.Add(nom); lignes.Add(nom);
                if (string.IsNullOrWhiteSpace(maison) || string.Equals(maison.Trim(), texte.Trim(), StringComparison.OrdinalIgnoreCase)) continue;
                float corps = nom.Corps * PART_DE_LA_MAISON;
                NomCourbe sous = Poser("Maison du pays " + id, id, maison, StyleDeNom.Capitales, trace.Dessous(nom.Corps * ECART_DE_LA_MAISON, corps / TraceDeNom.PART_DE_LA_LARGEUR));
                if (sous == null) continue;
                sous.NomDuPays = nom; nom.Maison = sous; lignes.Add(sous);
            }
        }

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
            string ecrit = Ecrit(texte, style);
            NomCompose compose = trace.Composer(Avances(ecrit, style));
            if (compose == null) return null;
            var objet = new GameObject(objetNomme, typeof(MeshFilter), typeof(MeshRenderer)); objet.transform.SetParent(racine, false);
            var maillage = new Mesh { name = "Nom de " + id }; maillage.MarkDynamic(); objet.GetComponent<MeshFilter>().sharedMesh = maillage;
            var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterials = matieres; rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false; rendu.enabled = false;
            return new NomCourbe(id, texte, ecrit, style, trace, compose, rendu, maillage);
        }

        // Règle chaque nom sur la vue : son opacité, son halo, la taille de ses lettres, et son maillage quand il le
        // faut ou que l'atlas a été refait. La maison suit la règle du nom à son propre corps, et jamais plus que lui :
        // elle se cache plus tôt de loin, et s'efface avec lui de près.
        public void Suivre(Camera camera)
        {
            if (camera == null || noms.Count == 0) return;
            float ecran = camera.pixelHeight;
            foreach (NomCourbe nom in lignes)
            {
                float px = CorpsALEcran(camera, nom), opacite = Opacite(px, ecran), force = ForceDuHalo(px); nom.CorpsPx = px;
                if (nom.NomDuPays != null) opacite = Mathf.Min(opacite, nom.NomDuPays.Opacite);
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
            noms.Clear(); lignes.Clear();
        }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(o); else UnityEngine.Object.DestroyImmediate(o); }
    }
}
