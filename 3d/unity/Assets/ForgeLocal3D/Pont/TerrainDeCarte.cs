using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;

namespace Forge.Pont {
    // Le terrain de la carte, levé d'un seul tenant depuis la carte servie (`GET /carte` : les cellules, leur relief) et
    // la forme de leurs lieux (`GET /formes`). Rien ici ne touche un objet d'Unity : le levé part hors du fil principal.
    // Les lieux sont numérotés dans l'ordre des cellules servies, puis par rang dans la cellule. Quatre grilles couvrent
    // le même rectangle, la boîte des lieux bordée de mer :
    // - les lieux : un texel tous les `Pas` km, 0 pour la mer, sinon le numéro du lieu + 1. Un texel est au lieu dont
    //   un polygone contient son centre (règle pair-impair, trous compris), et à la cellule de ce lieu. Un lieu plus
    //   petit qu'un texel en reçoit un quand même, pris à la mer ou à un voisin qui en garde : aucun lieu servi ne
    //   disparaît. Le bord commun de deux lieux est servi deux fois, une par lieu, et si les deux tracés s'écartent ou
    //   se recouvrent, celui du lieu du plus petit numéro fait foi. Il garde les texels recouverts, et la mer prise
    //   entre les deux tracés va à l'autre ;
    // - les bords : pour chaque texel, la distance au plus proche bord de son lieu (pour la mer, au plus proche
    //   rivage), et la distance à la plus proche côte. Ces distances se mesurent aux côtés servis eux-mêmes, pas à
    //   la grille : un trait tiré d'elles reste net bien en dessous du texel ;
    // - le relief : une altitude tous les `PasDuRelief` km, positive à terre, nulle au rivage, négative en mer ;
    // - le maillage : un sommet tous les `PasDuMaillage` km, à son altitude, la plus haute cime possible au plan 0.
    //   Tout le terrain reste donc sous les calques posés à plat au-dessus de ce plan.
    // Le relief est un décor : il ne vient d'aucune mesure et ne décide aucune grandeur du monde. Il habille la classe
    // de relief servie de la cellule de chaque lieu, plus haute et plus heurtée de la plaine à la haute montagne, et
    // s'efface vers la côte. Il ne dépend que de la carte et des formes : deux levés des mêmes sont égaux.
    // Les frontières ne sont pas levées : elles dépendent de qui tient chaque lieu, et se mesurent à la demande dans une
    // grille de plus (`Frontieres`), aux mêmes côtés. La marque d'une cellule se mesure de même (`Marque`), à ses côtés
    // avec tout ce qui n'est pas elle, la mer comprise. Rien ici ne se dessine sans les formes : sans elles, pas de terrain.
    // La carte servie s'arrête quelque part sur la terre (l'est de l'Anatolie, le sud de l'Égypte) : les côtés qui l'y
    // coupent sont droits et posés sur l'enveloppe convexe de toutes les terres, qu'ils couvrent sur des centaines de km,
    // quand une vraie côte ne la touche qu'en quelques caps. Une arête de l'enveloppe longue d'au moins `ARETE_MIN_KM`,
    // couverte au moins à `COUVERTURE_MIN` par des côtés qui en sont à moins de `ECART_DE_COUPE_KM`, est une coupe ; ces
    // côtés sont `Coupes`. La mer qui est hors de l'enveloppe et plus près d'une coupe que de toute autre arête est hors
    // de la carte (`HorsCarteEn`) : le dessin y met du papier, et la terre ne plonge pas vers elle comme vers une côte.
    public sealed class TerrainDeCarte {
        public const float MARGE_DE_MER_KM = 160f, PAS_MINIMAL_KM = 1f;
        public const int COTE_MAXIMAL = 4096, TEXELS_PAR_RELIEF = 2, TEXELS_PAR_MAILLE = 8;
        // En km de décor : la plus haute cime possible, le fond de la mer au large, et la terre au ras de l'eau.
        public const float PLAFOND = 40f, FOND = 6f, RIVAGE = 0.15f;
        // La côte monte sur COTE_KM ; le fond descend sur LARGE_KM, vite près du rivage puis de moins en moins, et se
        // lisse sur FLOU_DE_MER_KM. Les deux ensemble tiennent dans la marge : le bord du terrain est au fond.
        private const double COTE_KM = 30, LARGE_KM = 130, FLOU_KM = 12, FLOU_DE_MER_KM = 7;
        // Le socle et le heurt de chaque classe servie, en km de décor ; le socle dépasse toujours le heurt.
        private static readonly Dictionary<string, (float socle, float heurt)> CLASSES = new Dictionary<string, (float, float)> {
            { "marais", (0.3f, 0.1f) }, { "plaine", (1.2f, 0.6f) }, { "colline", (5f, 2.5f) },
            { "montagne", (14f, 7f) }, { "haute_montagne", (26f, 12f) }
        };
        // Les classes servies, du marais à la haute montagne, et leur socle en km de décor : les paliers d'une teinte d'altitude.
        public static readonly IReadOnlyList<(string classe, float socle)> PALIERS = new List<(string, float)> {
            ("marais", CLASSES["marais"].socle), ("plaine", CLASSES["plaine"].socle), ("colline", CLASSES["colline"].socle),
            ("montagne", CLASSES["montagne"].socle), ("haute_montagne", CLASSES["haute_montagne"].socle)
        }.AsReadOnly();
        private const string SANS_CLASSE = "plaine"; // un relief non servi, ou d'une classe inconnue, se dessine en plaine
        // Deux tracés du même bord s'écartent de moins de deux fois FENTE_KM : une mer plus étroite entre deux lieux
        // est une fente du service, et se comble.
        public const float FENTE_KM = 1.3f;
        // Au-delà de sa portée, une distance ne se mesure plus : elle vaut la portée.
        public const float PORTEE_DES_BORDS_KM = 12f, PORTEE_DES_FRONTIERES_KM = 16f, PORTEE_DE_LA_MARQUE_KM = 16f;
        // Une coupe de la carte : une arête de l'enveloppe d'au moins ARETE_MIN_KM, couverte à COUVERTURE_MIN par des côtés
        // à moins de ECART_DE_COUPE_KM d'elle.
        public const double ARETE_MIN_KM = 30, COUVERTURE_MIN = 0.5, ECART_DE_COUPE_KM = 1;
        // Les arêtes non couvertes, entre deux coupes, sur moins de COMBLE_MAX_KM : au-delà de la carte comme elles.
        public const double COMBLE_MAX_KM = 800;
        public const byte AU_LOIN = 255; // l'octet d'une distance au moins égale à la portée
        private const int BANDE = 64; // les lignes de texels qu'une même tâche mesure

        // Un morceau de côté servi qui sépare deux lieux sur la grille : celui qui le sert, celui d'en face (0 pour la
        // mer), en numéros de texel, et ses deux bouts en texels.
        private struct Morceau { public ushort Dedans, Dehors; public float Ax, Az, Bx, Bz; }
        // Les deux lieux les plus proches d'un texel de mer : leur numéro, leur distance, et vers où ils sont.
        private struct Proches { public int R1, R2; public double D1, X1, Z1, D2, X2, Z2; }

        private readonly ushort[] lieux; private readonly int[] texels; private readonly float[] altitudes;
        private readonly byte[] bords; private readonly Morceau[] morceaux; private readonly RectInt[] zones;
        // La cellule de chaque numéro de texel (0 pour la mer, sinon le rang servi + 1), le premier lieu de chaque
        // cellule (le dernier élément compte tous les lieux), le rang servi de chaque lieu dans sa cellule, et la boîte
        // de chaque cellule en texels.
        private readonly ushort[] cellulesDesNumeros; private readonly int[] premiers, rangs; private readonly RectInt[] zonesDesCellules;
        private readonly Vector3[] sommets; private readonly Vector2[] uv; private readonly int[] triangles;
        private readonly double minX, minZ, pas;
        // Deux octets par altitude : 255 si la mer y est hors de la carte, 0 sinon ; puis sa proximité à la coupe, de 255
        // sur elle à 0 à la marge de mer. Et les côtés qui coupent la carte, en km locaux : (ax, az, bx, bz).
        private readonly byte[] horsCarte; private readonly Vector4[] coupes;

        public PointCarte Origine { get; }
        // La boîte des lieux, en km locaux, sans la marge de mer.
        public Bounds Boite { get; }
        public int Largeur { get; }
        public int Hauteur { get; }
        public float Pas { get; }
        public float PasDuRelief => Pas * TEXELS_PAR_RELIEF;
        public float PasDuMaillage => Pas * TEXELS_PAR_MAILLE;
        public int LargeurDuRelief => Largeur / TEXELS_PAR_RELIEF;
        public int HauteurDuRelief => Hauteur / TEXELS_PAR_RELIEF;
        // Le coin sud-ouest du rectangle, en km locaux : le texel (0, 0) part de là, vers l'est puis vers le nord.
        public Vector2 Coin => new Vector2((float)minX, (float)minZ);
        // Le numéro de chaque texel : 0 pour la mer, sinon le lieu + 1.
        public IReadOnlyList<ushort> Lieux => lieux;
        public IReadOnlyList<float> Altitudes => altitudes;
        // Deux octets par texel : la distance au bord de son lieu, puis à la côte (`Distance` les rend en km).
        public IReadOnlyList<byte> Bords => bords;
        // Combien de morceaux de côtés séparent deux lieux, ou un lieu et la mer.
        public int Separations => morceaux.Length;
        public IReadOnlyList<Vector3> Sommets => sommets;
        public IReadOnlyList<Vector2> Uv => uv;
        public IReadOnlyList<int> Triangles => triangles;
        public int NombreDeLieux => texels.Length;
        // Le premier lieu de la cellule de ce rang servi, et combien elle en a : ses lieux se suivent, par rang.
        public int PremierLieuDe(int rang) => premiers[rang];
        public int LieuxDe(int rang) => premiers[rang + 1] - premiers[rang];
        // Le rang servi de la cellule d'un lieu, et le rang du lieu dans sa cellule.
        public int CelluleDuLieu(int lieu) => cellulesDesNumeros[lieu + 1] - 1;
        public int RangDuLieu(int lieu) => rangs[lieu];
        // Le lieu de ce rang dans la cellule de ce rang servi ; -1 si elle n'en sert pas.
        public int LieuDe(int rangDeCellule, long rangDuLieu) {
            for (int l = premiers[rangDeCellule]; l < premiers[rangDeCellule + 1]; l++) if (rangs[l] == rangDuLieu) return l;
            return -1;
        }
        // Combien de texels porte un lieu, et la cellule de ce rang servi : la somme de ses lieux.
        public int TexelsDuLieu(int lieu) => texels[lieu];
        public int TexelsDe(int rang) { int somme = 0; for (int l = premiers[rang]; l < premiers[rang + 1]; l++) somme += texels[l]; return somme; }
        // Les texels où un lieu, ou la cellule de ce rang servi, peut se trouver, et ceux de tout le terrain.
        public RectInt ZoneDuLieu(int lieu) => zones[lieu];
        public RectInt ZoneDe(int rang) => zonesDesCellules[rang];
        public RectInt Tout => new RectInt(0, 0, Largeur, Hauteur);
        internal ushort[] TexelsDesLieux => lieux;
        // La cellule de chaque numéro de texel : 0 pour la mer, sinon le rang servi + 1.
        internal ushort[] CellulesDesNumeros => cellulesDesNumeros;
        internal byte[] TexelsDesBords => bords;
        internal float[] TexelsDuRelief => altitudes;
        internal Vector3[] SommetsDuMaillage => sommets;
        internal Vector2[] UvDuMaillage => uv;
        internal int[] TrianglesDuMaillage => triangles;
        internal byte[] TexelsHorsCarte => horsCarte;
        // Les côtés de lieux qui coupent la carte sur la terre, en km locaux : (ax, az, bx, bz).
        public IReadOnlyList<Vector4> Coupes => coupes;
        // La mer sous un point en km locaux est-elle hors de la carte, au-delà d'une coupe ? Faux à terre et hors du rectangle.
        public bool HorsCarteEn(float x, float z) {
            int i = (int)Math.Floor((x - minX) / (pas * TEXELS_PAR_RELIEF)), j = (int)Math.Floor((z - minZ) / (pas * TEXELS_PAR_RELIEF));
            return i >= 0 && j >= 0 && i < LargeurDuRelief && j < HauteurDuRelief && horsCarte[2 * (j * LargeurDuRelief + i)] != 0;
        }

        private TerrainDeCarte(PointCarte origine, Bounds boite, int largeur, int hauteur, double pas, double minX, double minZ, ushort[] lieux, int[] texels, float[] altitudes, byte[] bords, Morceau[] morceaux, RectInt[] zones,
            ushort[] cellulesDesNumeros, int[] premiers, int[] rangs, RectInt[] zonesDesCellules, byte[] horsCarte, Vector4[] coupes) {
            this.horsCarte = horsCarte; this.coupes = coupes;
            Origine = origine; Boite = boite; Largeur = largeur; Hauteur = hauteur; Pas = (float)pas; this.pas = pas; this.minX = minX; this.minZ = minZ;
            this.lieux = lieux; this.texels = texels; this.altitudes = altitudes; this.bords = bords; this.morceaux = morceaux; this.zones = zones;
            this.cellulesDesNumeros = cellulesDesNumeros; this.premiers = premiers; this.rangs = rangs; this.zonesDesCellules = zonesDesCellules;
            int nx = largeur / TEXELS_PAR_MAILLE + 1, nz = hauteur / TEXELS_PAR_MAILLE + 1; double maille = pas * TEXELS_PAR_MAILLE;
            sommets = new Vector3[nx * nz]; uv = new Vector2[nx * nz]; triangles = new int[(nx - 1) * (nz - 1) * 6];
            for (int j = 0; j < nz; j++)
                for (int i = 0; i < nx; i++) {
                    float x = (float)(minX + i * maille), z = (float)(minZ + j * maille);
                    sommets[j * nx + i] = new Vector3(x, Altitude(x, z) - PLAFOND, z);
                    uv[j * nx + i] = new Vector2(i * TEXELS_PAR_MAILLE / (float)largeur, j * TEXELS_PAR_MAILLE / (float)hauteur);
                }
            int t = 0; // deux triangles par maille, tournés vers le haut
            for (int j = 0; j + 1 < nz; j++)
                for (int i = 0; i + 1 < nx; i++) {
                    int a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
                    triangles[t++] = a; triangles[t++] = c; triangles[t++] = b; triangles[t++] = b; triangles[t++] = c; triangles[t++] = d;
                }
        }

        // Le lieu du texel sous un point en km locaux : 0 pour la mer ou hors du rectangle, sinon le lieu + 1.
        public ushort LieuEn(float x, float z) {
            int i = (int)Math.Floor((x - minX) / pas), j = (int)Math.Floor((z - minZ) / pas);
            return i < 0 || j < 0 || i >= Largeur || j >= Hauteur ? (ushort)0 : lieux[j * Largeur + i];
        }
        // La cellule de ce même texel : 0 pour la mer ou hors du rectangle, sinon le rang servi + 1.
        public ushort CelluleEn(float x, float z) => cellulesDesNumeros[LieuEn(x, z)];

        // La distance en km que dit l'octet d'une grille de distances : son carré, pour que les petites distances, celles
        // qui placent un trait, soient les plus fines. `AU_LOIN` rend la portée.
        public static float Distance(byte code, float portee) => portee * (code / 255f) * (code / 255f);
        // Sous un point en km locaux, la distance au plus proche bord du lieu du texel, puis à la plus proche côte ;
        // hors du rectangle, la portée.
        public float BordEn(float x, float z) => Distance(Octet(bords, 2, 0, x, z), PORTEE_DES_BORDS_KM);
        public float CoteEn(float x, float z) => Distance(Octet(bords, 2, 1, x, z), PORTEE_DES_BORDS_KM);
        // La même lecture dans une grille mesurée par `Frontieres`, puis par `Marque`.
        public float FrontiereEn(byte[] champ, float x, float z) => Distance(Octet(champ, 1, 0, x, z), PORTEE_DES_FRONTIERES_KM);
        public float MarqueEn(byte[] champ, float x, float z) => Distance(Octet(champ, 1, 0, x, z), PORTEE_DE_LA_MARQUE_KM);

        // Mesure dans `champ`, un octet par texel, la distance de chaque texel au bord de la cellule de ce rang servi :
        // un côté entre l'un de ses lieux et un lieu d'une autre cellule ou la mer. Seule sa zone, élargie de la portée, est
        // mesurée ; celle de la cellule marquée d'avant (`avant`, -1 sans elle) revient d'abord au loin. Un rang -1 ne
        // marque rien.
        public void Marque(int rang, int avant, byte[] champ) {
            if (champ == null || champ.Length != Largeur * Hauteur) throw new ArgumentException("un octet par texel");
            var groupes = new int[texels.Length + 1]; double portee = PORTEE_DE_LA_MARQUE_KM / pas;
            if (avant >= 0) Porter(lieux, Largeur, morceaux, champ, 1, 0, groupes, portee, Elargie(zonesDesCellules[avant], portee));
            if (rang < 0) return;
            for (int l = premiers[rang]; l < premiers[rang + 1]; l++) groupes[l + 1] = 1;
            Porter(lieux, Largeur, morceaux, champ, 1, 0, groupes, portee, Elargie(zonesDesCellules[rang], portee));
        }
        private RectInt Elargie(RectInt zone, double portee) {
            int marge = (int)Math.Ceiling(portee) + 1, i0 = Math.Max(0, zone.xMin - marge), j0 = Math.Max(0, zone.yMin - marge);
            return new RectInt(i0, j0, Math.Min(Largeur, zone.xMax + marge) - i0, Math.Min(Hauteur, zone.yMax + marge) - j0);
        }
        private static void Porter(ushort[] lieux, int largeur, Morceau[] morceaux, byte[] champ, int saut, int decalage, int[] groupes, double portee, RectInt zone) =>
            Porter(lieux, largeur, morceaux, champ, saut, decalage, groupes, portee, zone.xMin, zone.yMin, zone.xMax, zone.yMax);
        private byte Octet(byte[] champ, int saut, int decalage, float x, float z) {
            int i = (int)Math.Floor((x - minX) / pas), j = (int)Math.Floor((z - minZ) / pas);
            return i < 0 || j < 0 || i >= Largeur || j >= Hauteur ? AU_LOIN : champ[(j * Largeur + i) * saut + decalage];
        }

        // Mesure dans `champ`, un octet par texel, la distance de chaque texel à la plus proche frontière de son pays :
        // un côté entre deux lieux de pays différents, qu'ils soient d'une même cellule ou de deux. `pays` dit le pays de
        // chaque lieu ; un pays négatif est hors du jeu, comme la mer : il n'a pas de frontière et n'en fait pas. Seuls
        // les texels de la zone, élargie de la portée, sont mesurés de nouveau : c'est assez quand seuls les lieux de la
        // zone ont changé de pays.
        public void Frontieres(IReadOnlyList<int> pays, byte[] champ, RectInt zone) {
            if (pays == null || pays.Count != texels.Length) throw new ArgumentException("un pays par lieu servi");
            if (champ == null || champ.Length != Largeur * Hauteur) throw new ArgumentException("un octet par texel");
            var groupes = new int[texels.Length + 1]; groupes[0] = -1;
            for (int l = 0; l < texels.Length; l++) groupes[l + 1] = pays[l];
            double portee = PORTEE_DES_FRONTIERES_KM / pas; int marge = (int)Math.Ceiling(portee) + 1;
            Porter(lieux, Largeur, morceaux, champ, 1, 0, groupes, portee,
                Math.Max(0, zone.xMin - marge), Math.Max(0, zone.yMin - marge), Math.Min(Largeur, zone.xMax + marge), Math.Min(Hauteur, zone.yMax + marge));
        }

        // L'altitude du relief sous un point en km locaux, lue entre les quatre altitudes voisines ; hors du rectangle, celle du bord.
        public float Altitude(float x, float z) {
            int l = LargeurDuRelief, h = HauteurDuRelief; double relief = pas * TEXELS_PAR_RELIEF;
            double u = Math.Min(Math.Max((x - minX) / relief - 0.5, 0), l - 1), v = Math.Min(Math.Max((z - minZ) / relief - 0.5, 0), h - 1);
            int i = Math.Min((int)u, l - 2), j = Math.Min((int)v, h - 2); double fu = u - i, fv = v - j;
            double bas = altitudes[j * l + i] + fu * (altitudes[j * l + i + 1] - altitudes[j * l + i]);
            double haut = altitudes[(j + 1) * l + i] + fu * (altitudes[(j + 1) * l + i + 1] - altitudes[(j + 1) * l + i]);
            return (float)(bas + fv * (haut - bas));
        }

        // La hauteur du maillage sous un point en km locaux, telle qu'il se dessine : lue sur le triangle qui porte le
        // point, entre ses trois sommets. Nulle à la plus haute cime possible, négative partout ailleurs ; hors du
        // rectangle, celle du bord.
        public float SolDuMaillage(float x, float z) {
            int nx = Largeur / TEXELS_PAR_MAILLE + 1, nz = Hauteur / TEXELS_PAR_MAILLE + 1; double maille = pas * TEXELS_PAR_MAILLE;
            double u = Math.Min(Math.Max((x - minX) / maille, 0), nx - 1), v = Math.Min(Math.Max((z - minZ) / maille, 0), nz - 1);
            int i = Math.Min((int)u, nx - 2), j = Math.Min((int)v, nz - 2); double fu = u - i, fv = v - j;
            float a = sommets[j * nx + i].y, b = sommets[j * nx + i + 1].y, c = sommets[(j + 1) * nx + i].y, d = sommets[(j + 1) * nx + i + 1].y;
            // Chaque maille est coupée du sommet de l'est à celui du nord.
            return fu + fv <= 1 ? (float)(a + fu * (b - a) + fv * (c - a)) : (float)(d + (1 - fu) * (c - d) + (1 - fv) * (b - d));
        }

        // Le pas des grilles pour un rectangle dont le plus grand côté, marge de mer comprise, fait tant de km : un texel
        // par km, sauf si le côté dépasse alors `COTE_MAXIMAL` texels.
        public static double PasPour(double coteKm) => Math.Max(PAS_MINIMAL_KM, coteKm / COTE_MAXIMAL);

        // Le terrain de la carte et de ses formes : chaque cellule servie doit avoir les siennes, au moins un lieu, et
        // chaque lieu un contour. Le relief de chaque lieu est celui de sa cellule.
        public static TerrainDeCarte Lever(CarteLue carte, FormesLues formes) {
            if (carte == null) throw new ArgumentNullException(nameof(carte));
            if (formes == null) throw new ArgumentNullException(nameof(formes));
            int n = carte.Cellules.Count;
            if (n == 0) throw new ArgumentException("une carte vide n'a aucun terrain");
            if (formes.Cellules.Count != n) throw new ArgumentException("des formes de " + formes.Cellules.Count + " cellules pour une carte de " + n);
            var lesFormes = new FormeDeCellule[n]; var premiers = new int[n + 1];
            for (int r = 0; r < n; r++) {
                long id = carte.Cellules[r].CellId;
                lesFormes[r] = formes.De(id) ?? throw new ArgumentException("cellule " + id + " : aucune forme servie");
                if (lesFormes[r].Lieux.Count == 0) throw new ArgumentException("cellule " + id + " : aucun lieu");
                premiers[r + 1] = premiers[r] + lesFormes[r].Lieux.Count;
            }
            int nombre = premiers[n];
            if (nombre >= ushort.MaxValue) throw new ArgumentException(nombre + " lieux : trop pour un terrain");
            PointCarte origine = MaillageDeCarte.Centre(carte);
            // Les anneaux en km locaux, x puis z, par lieu puis par polygone ; la boîte de tous leurs points.
            var polygones = new List<List<double[]>>[nombre]; var cellulesDesNumeros = new ushort[nombre + 1]; var rangs = new int[nombre];
            double x0 = double.PositiveInfinity, z0 = double.PositiveInfinity, x1 = double.NegativeInfinity, z1 = double.NegativeInfinity;
            for (int r = 0; r < n; r++)
                for (int k = 0; k < lesFormes[r].Lieux.Count; k++) {
                    FormeDeLieu lieu = lesFormes[r].Lieux[k]; int l = premiers[r] + k, points = 0;
                    polygones[l] = new List<List<double[]>>(); cellulesDesNumeros[l + 1] = (ushort)(r + 1); rangs[l] = (int)lieu.Rang;
                    foreach (PolygoneDeCarte polygone in lieu.Contour) {
                        var anneaux = new List<double[]>();
                        for (int a = -1; a < polygone.Trous.Count; a++) {
                            IReadOnlyList<PointCarte> anneau = a < 0 ? polygone.Exterieur : polygone.Trous[a];
                            var local = new double[anneau.Count * 2];
                            for (int p = 0; p < anneau.Count; p++) {
                                double x = (anneau[p].X - origine.X) / 1000.0, z = (anneau[p].Y - origine.Y) / 1000.0; local[2 * p] = x; local[2 * p + 1] = z;
                                if (x < x0) x0 = x; if (x > x1) x1 = x; if (z < z0) z0 = z; if (z > z1) z1 = z;
                            }
                            anneaux.Add(local); points += anneau.Count;
                        }
                        polygones[l].Add(anneaux);
                    }
                    if (points == 0) throw new ArgumentException("cellule " + carte.Cellules[r].CellId + ", lieu " + lieu.Rang + " : aucun contour");
                }
            var boite = new Bounds(); boite.SetMinMax(new Vector3((float)x0, 0f, (float)z0), new Vector3((float)x1, 0f, (float)z1));
            double minX = x0 - MARGE_DE_MER_KM, minZ = z0 - MARGE_DE_MER_KM, large = x1 - x0 + 2 * MARGE_DE_MER_KM, haut = z1 - z0 + 2 * MARGE_DE_MER_KM;
            double pas = PasPour(Math.Max(large, haut));
            int largeur = ParMailles(large / pas), hauteur = ParMailles(haut / pas);

            var lieux = new ushort[largeur * hauteur]; var texels = new int[nombre];
            // Du dernier lieu au premier : un texel que deux lieux recouvrent reste à celui du plus petit numéro.
            for (int l = nombre - 1; l >= 0; l--)
                foreach (List<double[]> polygone in polygones[l]) Remplir(lieux, texels, largeur, hauteur, minX, minZ, pas, polygone, (ushort)(l + 1));
            for (int l = 0; l < nombre; l++)
                if (texels[l] == 0) Garantir(lieux, texels, largeur, hauteur, minX, minZ, pas, polygones[l][0][0], (ushort)(l + 1));
            Combler(lieux, texels, largeur, hauteur, minX, minZ, pas, polygones);

            var socles = new float[nombre]; var heurts = new float[nombre];
            for (int l = 0; l < nombre; l++) {
                string classe = carte.Cellules[cellulesDesNumeros[l + 1] - 1].Relief;
                (socles[l], heurts[l]) = classe != null && CLASSES.TryGetValue(classe, out var valeurs) ? valeurs : CLASSES[SANS_CLASSE];
            }
            Enveloppe enveloppe = Envelopper(polygones, out Vector4[] coupes);
            var horsCarte = new byte[2 * (largeur / TEXELS_PAR_RELIEF) * (hauteur / TEXELS_PAR_RELIEF)];
            float[] altitudes = Relief(lieux, largeur, hauteur, minX, minZ, pas, socles, heurts, enveloppe, horsCarte);

            Morceau[] morceaux = Separer(lieux, largeur, hauteur, minX, minZ, pas, polygones);
            // Les bords : chaque lieu est son propre groupe. Les côtes : toute la terre est un groupe, la mer l'autre.
            var chacun = new int[nombre + 1]; var terre = new int[nombre + 1];
            for (int v = 1; v <= nombre; v++) { chacun[v] = v; terre[v] = 1; }
            var bords = new byte[2 * largeur * hauteur];
            Porter(lieux, largeur, morceaux, bords, 2, 0, chacun, PORTEE_DES_BORDS_KM / pas, 0, 0, largeur, hauteur);
            Porter(lieux, largeur, morceaux, bords, 2, 1, terre, PORTEE_DES_BORDS_KM / pas, 0, 0, largeur, hauteur);
            // La boîte de chaque lieu en texels, élargie de ce que le comblement ou un texel garanti peut lui ajouter ; celle
            // d'une cellule tient tous ses lieux.
            var zones = new RectInt[nombre]; var zonesDesCellules = new RectInt[n]; int ajout = (int)Math.Ceiling(FENTE_KM / pas) + 3;
            for (int l = 0; l < nombre; l++) {
                double ax = double.PositiveInfinity, az = double.PositiveInfinity, bx = double.NegativeInfinity, bz = double.NegativeInfinity;
                foreach (List<double[]> polygone in polygones[l])
                    for (int k = 0; k + 1 < polygone[0].Length; k += 2) { ax = Math.Min(ax, polygone[0][k]); bx = Math.Max(bx, polygone[0][k]); az = Math.Min(az, polygone[0][k + 1]); bz = Math.Max(bz, polygone[0][k + 1]); }
                int i0 = Math.Max(0, (int)Math.Floor((ax - minX) / pas) - ajout), j0 = Math.Max(0, (int)Math.Floor((az - minZ) / pas) - ajout);
                int i1 = Math.Min(largeur, (int)Math.Ceiling((bx - minX) / pas) + ajout), j1 = Math.Min(hauteur, (int)Math.Ceiling((bz - minZ) / pas) + ajout);
                zones[l] = new RectInt(i0, j0, Math.Max(0, i1 - i0), Math.Max(0, j1 - j0));
            }
            for (int r = 0; r < n; r++) {
                RectInt u = zones[premiers[r]];
                for (int l = premiers[r] + 1; l < premiers[r + 1]; l++) {
                    RectInt v = zones[l]; int ax = Math.Min(u.xMin, v.xMin), az = Math.Min(u.yMin, v.yMin);
                    u = new RectInt(ax, az, Math.Max(u.xMax, v.xMax) - ax, Math.Max(u.yMax, v.yMax) - az);
                }
                zonesDesCellules[r] = u;
            }
            return new TerrainDeCarte(origine, boite, largeur, hauteur, pas, minX, minZ, lieux, texels, altitudes, bords, morceaux, zones, cellulesDesNumeros, premiers, rangs, zonesDesCellules, horsCarte, coupes);
        }

        // L'enveloppe convexe des terres, ses sommets dans le sens trigonométrique (l'arête k va du sommet k au suivant), et
        // si chaque arête est une coupe de la carte.
        private sealed class Enveloppe { public double[] X, Z; public bool[] Coupee; }

        // L'enveloppe des anneaux extérieurs de tous les lieux, et les côtés qui en couvrent les coupes.
        private static Enveloppe Envelopper(List<List<double[]>>[] polygones, out Vector4[] coupes) {
            var points = new List<(double x, double z)>();
            foreach (List<List<double[]>> lieu in polygones)
                foreach (List<double[]> polygone in lieu)
                    for (int k = 0; k + 1 < polygone[0].Length; k += 2) points.Add((polygone[0][k], polygone[0][k + 1]));
            points.Sort();
            double Croix((double x, double z) o, (double x, double z) a, (double x, double z) b) => (a.x - o.x) * (b.z - o.z) - (a.z - o.z) * (b.x - o.x);
            var bas = new List<(double x, double z)>(); var haut = new List<(double x, double z)>();
            foreach (var q in points) { while (bas.Count >= 2 && Croix(bas[bas.Count - 2], bas[bas.Count - 1], q) <= 0) bas.RemoveAt(bas.Count - 1); bas.Add(q); }
            for (int i = points.Count - 1; i >= 0; i--) { var q = points[i]; while (haut.Count >= 2 && Croix(haut[haut.Count - 2], haut[haut.Count - 1], q) <= 0) haut.RemoveAt(haut.Count - 1); haut.Add(q); }
            bas.RemoveAt(bas.Count - 1); haut.RemoveAt(haut.Count - 1); bas.AddRange(haut);
            int n = bas.Count; var env = new Enveloppe { X = new double[n], Z = new double[n], Coupee = new bool[n] };
            for (int k = 0; k < n; k++) { env.X[k] = bas[k].x; env.Z[k] = bas[k].z; }
            // Chaque côté extérieur dont les deux bouts sont à moins de l'écart d'une arête assez longue, et entre ses bouts,
            // couvre une part de cette arête.
            var couvertes = new List<(double debut, double fin)>[n]; var poses = new List<(int arete, Vector4 cote)>();
            var longues = new List<int>(); var vx = new double[n]; var vz = new double[n]; var longueurs = new double[n];
            for (int k = 0; k < n; k++) {
                vx[k] = env.X[(k + 1) % n] - env.X[k]; vz[k] = env.Z[(k + 1) % n] - env.Z[k]; longueurs[k] = Math.Sqrt(vx[k] * vx[k] + vz[k] * vz[k]);
                if (longueurs[k] >= ARETE_MIN_KM) longues.Add(k);
            }
            foreach (List<List<double[]>> lieu in polygones)
                foreach (List<double[]> polygone in lieu) {
                    double[] a = polygone[0];
                    for (int c = 0; c + 3 < a.Length; c += 2)
                        foreach (int k in longues) {
                            double ux = vx[k], uz = vz[k], longueur = longueurs[k];
                            double Ecart(double x, double z) => Math.Abs(ux * (z - env.Z[k]) - uz * (x - env.X[k])) / longueur;
                            double Le(double x, double z) => (ux * (x - env.X[k]) + uz * (z - env.Z[k])) / (longueur * longueur);
                            if (Ecart(a[c], a[c + 1]) > ECART_DE_COUPE_KM || Ecart(a[c + 2], a[c + 3]) > ECART_DE_COUPE_KM) continue;
                            double t0 = Le(a[c], a[c + 1]), t1 = Le(a[c + 2], a[c + 3]);
                            if (Math.Min(t0, t1) < -0.01 || Math.Max(t0, t1) > 1.01) continue;
                            (couvertes[k] ?? (couvertes[k] = new List<(double, double)>())).Add((Math.Min(t0, t1), Math.Max(t0, t1)));
                            poses.Add((k, new Vector4((float)a[c], (float)a[c + 1], (float)a[c + 2], (float)a[c + 3]))); break;
                        }
                }
            for (int k = 0; k < n; k++) {
                if (couvertes[k] == null) continue;
                couvertes[k].Sort(); double couvert = 0, jusque = double.NegativeInfinity;
                foreach (var (debut, fin) in couvertes[k]) { double d = Math.Max(debut, jusque); if (fin > d) { couvert += fin - d; jusque = fin; } }
                env.Coupee[k] = couvert >= COUVERTURE_MIN;
            }
            var lesCoupes = new List<Vector4>(); foreach (var (arete, cote) in poses) if (env.Coupee[arete]) lesCoupes.Add(cote);
            // Une suite d'arêtes qu'aucun côté ne couvre, entre deux coupes, plus courte que `COMBLE_MAX_KM`, est au-delà de la carte
            // elle aussi : une terre qui lui manque (le Levant, entre le Sinaï et l'Anatolie), ou un creux de la coupe que
            // l'enveloppe enjambe. Sans cela, la mer y rayerait le papier. Une côte, qui court sur des milliers de km, n'en est pas une.
            var coupees = (bool[])env.Coupee.Clone();
            for (int k = 0; k < n; k++)
            {
                if (!coupees[k] || coupees[(k + 1) % n]) continue;
                double suite = 0; int j = (k + 1) % n;
                while (!coupees[j] && j != k) { suite += longueurs[j]; j = (j + 1) % n; }
                if (j == k || suite > COMBLE_MAX_KM) continue;
                for (int m = (k + 1) % n; m != j; m = (m + 1) % n) env.Coupee[m] = true;
            }
            coupes = lesCoupes.ToArray(); return env;
        }

        // Pour chaque altitude de mer hors de l'enveloppe, l'arête la plus proche : si c'est une coupe, la mer y est hors
        // de la carte, et sa proximité à la coupe s'écrit, de 255 sur elle à 0 à la marge de mer.
        private static bool[] HorsDeLaCarte(bool[] terre, int l, int h, double minX, double minZ, double pas, Enveloppe env, byte[] sortie) {
            var hors = new bool[l * h]; int n = env.X.Length; if (Array.IndexOf(env.Coupee, true) < 0) return hors;
            Parallel.For(0, h, j => {
                double z = minZ + (j + 0.5) * pas;
                for (int i = 0; i < l; i++) {
                    int k = j * l + i; if (terre[k]) continue;
                    double x = minX + (i + 0.5) * pas, plusPres = double.PositiveInfinity; int arete = -1; bool dehors = false;
                    for (int e = 0; e < n; e++) {
                        double ax = env.X[e], az = env.Z[e], ux = env.X[(e + 1) % n] - ax, uz = env.Z[(e + 1) % n] - az, l2 = ux * ux + uz * uz;
                        if (ux * (z - az) - uz * (x - ax) < 0) dehors = true; // à droite d'une arête : hors de l'enveloppe
                        double t = l2 > 0 ? Math.Min(Math.Max(((x - ax) * ux + (z - az) * uz) / l2, 0), 1) : 0, dx = x - ax - t * ux, dz = z - az - t * uz, d = dx * dx + dz * dz;
                        if (d < plusPres) { plusPres = d; arete = e; }
                    }
                    if (!dehors || !env.Coupee[arete]) continue;
                    hors[k] = true; sortie[2 * k] = 255;
                    sortie[2 * k + 1] = (byte)Math.Round(255 * (1 - Math.Min(Math.Sqrt(plusPres), MARGE_DE_MER_KM) / MARGE_DE_MER_KM));
                }
            });
            return hors;
        }
        // Le nombre de texels d'un côté : assez pour le couvrir, en mailles entières.
        private static int ParMailles(double texels) => Math.Max(2, (int)Math.Ceiling(texels / TEXELS_PAR_MAILLE)) * TEXELS_PAR_MAILLE;

        private static void Prendre(ushort[] lieux, int[] texels, int index, ushort valeur) {
            ushort avant = lieux[index]; if (avant == valeur) return;
            if (avant != 0) texels[avant - 1]--;
            lieux[index] = valeur; texels[valeur - 1]++;
        }

        // Ligne de texels par ligne : les centres pris entre deux croisements du bord, l'ouest compris, l'est exclu, pour
        // que deux lieux voisins ne prennent jamais le même texel.
        private static void Remplir(ushort[] lieux, int[] texels, int largeur, int hauteur, double minX, double minZ, double pas, List<double[]> polygone, ushort valeur) {
            double bas = double.PositiveInfinity, haut = double.NegativeInfinity;
            foreach (double[] anneau in polygone) for (int k = 1; k < anneau.Length; k += 2) { if (anneau[k] < bas) bas = anneau[k]; if (anneau[k] > haut) haut = anneau[k]; }
            int j0 = Math.Max(0, (int)Math.Ceiling((bas - minZ) / pas - 0.5)), j1 = Math.Min(hauteur - 1, (int)Math.Floor((haut - minZ) / pas - 0.5));
            var croisements = new List<double>();
            for (int j = j0; j <= j1; j++) {
                double z = minZ + (j + 0.5) * pas; croisements.Clear();
                foreach (double[] a in polygone)
                    for (int k = 0; k + 3 < a.Length; k += 2)
                        if ((a[k + 1] > z) != (a[k + 3] > z)) croisements.Add(a[k] + (z - a[k + 1]) / (a[k + 3] - a[k + 1]) * (a[k + 2] - a[k]));
                croisements.Sort();
                for (int c = 0; c + 1 < croisements.Count; c += 2) {
                    int i0 = Math.Max(0, (int)Math.Ceiling((croisements[c] - minX) / pas - 0.5)), i1 = Math.Min(largeur, (int)Math.Ceiling((croisements[c + 1] - minX) / pas - 0.5));
                    for (int i = i0; i < i1; i++) Prendre(lieux, texels, j * largeur + i, valeur);
                }
            }
        }

        // Un lieu qu'aucun centre de texel ne touche prend le texel de son premier anneau, ou le plus proche qui soit
        // à la mer ou à un lieu qui en garde un autre. Faute d'un tel texel, il reste sans texel, et cela se compte.
        private static void Garantir(ushort[] lieux, int[] texels, int largeur, int hauteur, double minX, double minZ, double pas, double[] anneau, ushort valeur) {
            double x = 0, z = 0; int points = anneau.Length / 2;
            for (int k = 0; k < points; k++) { x += anneau[2 * k]; z += anneau[2 * k + 1]; }
            int ci = Math.Min(Math.Max((int)Math.Floor((x / points - minX) / pas), 0), largeur - 1), cj = Math.Min(Math.Max((int)Math.Floor((z / points - minZ) / pas), 0), hauteur - 1);
            for (int rayon = 0; rayon <= 2; rayon++)
                for (int dj = -rayon; dj <= rayon; dj++)
                    for (int di = -rayon; di <= rayon; di++) {
                        if (Math.Max(Math.Abs(di), Math.Abs(dj)) != rayon) continue;
                        int i = ci + di, j = cj + dj; if (i < 0 || j < 0 || i >= largeur || j >= hauteur) continue;
                        ushort avant = lieux[j * largeur + i];
                        if (avant != 0 && texels[avant - 1] < 2) continue;
                        Prendre(lieux, texels, j * largeur + i, valeur); return;
                    }
        }

        // Un texel de mer pris entre deux lieux, à moins de FENTE_KM de chacun et l'un en face de l'autre, est dans
        // une fente entre deux tracés du même bord : il va à celui du plus grand numéro, et la grille suit ainsi le tracé
        // de l'autre. Un détroit plus étroit que deux fois FENTE_KM entre deux lieux se ferme donc au dessin.
        private static void Combler(ushort[] lieux, int[] texels, int largeur, int hauteur, double minX, double minZ, double pas, List<List<double[]>>[] polygones) {
            double portee = FENTE_KM / pas; var proches = new Dictionary<int, Proches>();
            for (int r = 0; r < polygones.Length; r++)
                foreach (List<double[]> polygone in polygones[r])
                    foreach (double[] a in polygone)
                        for (int k = 0; k + 3 < a.Length; k += 2) {
                            double ax = (a[k] - minX) / pas, az = (a[k + 1] - minZ) / pas, dx = (a[k + 2] - minX) / pas - ax, dz = (a[k + 3] - minZ) / pas - az;
                            double l2 = dx * dx + dz * dz, inv = l2 > 0 ? 1 / l2 : 0;
                            int i0 = Math.Max(0, (int)Math.Ceiling(Math.Min(ax, ax + dx) - portee - 0.5)), i1 = Math.Min(largeur - 1, (int)Math.Floor(Math.Max(ax, ax + dx) + portee - 0.5));
                            int j0 = Math.Max(0, (int)Math.Ceiling(Math.Min(az, az + dz) - portee - 0.5)), j1 = Math.Min(hauteur - 1, (int)Math.Floor(Math.Max(az, az + dz) + portee - 0.5));
                            for (int j = j0; j <= j1; j++)
                                for (int i = i0; i <= i1; i++) {
                                    int index = j * largeur + i; if (lieux[index] != 0) continue;
                                    double px = i + 0.5 - ax, pz = j + 0.5 - az, t = Math.Min(Math.Max((px * dx + pz * dz) * inv, 0), 1);
                                    double x = t * dx - px, z = t * dz - pz, d = Math.Sqrt(x * x + z * z); if (d >= portee) continue;
                                    if (!proches.TryGetValue(index, out Proches p)) p = new Proches { R1 = -1, R2 = -1 };
                                    if (p.R1 == r) { if (d < p.D1) { p.D1 = d; p.X1 = x; p.Z1 = z; } }
                                    else if (p.R1 < 0 || d < p.D1) { p.R2 = p.R1; p.D2 = p.D1; p.X2 = p.X1; p.Z2 = p.Z1; p.R1 = r; p.D1 = d; p.X1 = x; p.Z1 = z; }
                                    else if (p.R2 == r) { if (d < p.D2) { p.D2 = d; p.X2 = x; p.Z2 = z; } }
                                    else if (p.R2 < 0 || d < p.D2) { p.R2 = r; p.D2 = d; p.X2 = x; p.Z2 = z; }
                                    proches[index] = p;
                                }
                        }
            foreach (KeyValuePair<int, Proches> paire in proches) {
                Proches p = paire.Value;
                if (p.R2 >= 0 && p.X1 * p.X2 + p.Z1 * p.Z2 <= 0) Prendre(lieux, texels, paire.Key, (ushort)(Math.Max(p.R1, p.R2) + 1));
            }
        }

        // Les côtés servis qui séparent vraiment deux lieux sur la grille, coupés en bouts d'un texel au plus, chacun
        // jugé en son milieu : la grille doit dire son lieu juste en dedans, et un autre, ou la mer, juste en dehors.
        // Le texel du milieu lui-même est lu, du dedans comme du dehors : d'une pointe de terre ou d'une entaille de mer
        // plus fine qu'un texel, la grille ne garde que des texels épars, que les sondes d'à côté enjambent.
        // Un côté qui longe l'intérieur d'un lieu (un tracé recouvert, le bord d'une fente comblée) ne sépare rien.
        // Entre deux lieux, seul le côté de celui du plus petit numéro est gardé : un bord n'a qu'un tracé. Les bouts
        // qui se suivent sur un même côté, face au même voisin, font un seul morceau.
        private static Morceau[] Separer(ushort[] lieux, int largeur, int hauteur, double minX, double minZ, double pas, List<List<double[]>>[] polygones) {
            var morceaux = new List<Morceau>();
            int Lue(double x, double z) {
                int i = (int)Math.Floor(x), j = (int)Math.Floor(z);
                return i < 0 || j < 0 || i >= largeur || j >= hauteur ? 0 : lieux[j * largeur + i];
            }
            for (int r = 0; r < polygones.Length; r++) {
                int soi = r + 1;
                foreach (List<double[]> polygone in polygones[r])
                    for (int a = 0; a < polygone.Count; a++) {
                        double[] anneau = polygone[a]; double aire = 0;
                        for (int k = 0; k + 3 < anneau.Length; k += 2) aire += anneau[k] * anneau[k + 3] - anneau[k + 2] * anneau[k + 1];
                        // Un anneau extérieur qui tourne à gauche, ou un trou qui tourne à droite, a le dehors du lieu à sa droite.
                        double sens = (aire > 0) == (a == 0) ? 1 : -1;
                        for (int k = 0; k + 3 < anneau.Length; k += 2) {
                            double ax = (anneau[k] - minX) / pas, az = (anneau[k + 1] - minZ) / pas, dx = (anneau[k + 2] - minX) / pas - ax, dz = (anneau[k + 3] - minZ) / pas - az;
                            double l = Math.Sqrt(dx * dx + dz * dz); if (l <= 0) continue;
                            double nx = sens * dz / l, nz = -sens * dx / l; // vers le dehors, long d'un texel
                            int bouts = Math.Max(1, (int)Math.Ceiling(l)), debut = 0, voisine = -1; // -1 : rien n'est séparé
                            for (int b = 0; b <= bouts; b++) {
                                int vue = -1;
                                if (b < bouts) {
                                    double mx = ax + (b + 0.5) / bouts * dx, mz = az + (b + 0.5) / bouts * dz;
                                    int dehors = Lue(mx, mz);
                                    if (dehors == soi || Lue(mx - 0.75 * nx, mz - 0.75 * nz) == soi || Lue(mx - 1.25 * nx, mz - 1.25 * nz) == soi) {
                                        if (dehors == soi) dehors = Lue(mx + 0.75 * nx, mz + 0.75 * nz);
                                        if (dehors == soi) dehors = Lue(mx + 1.5 * nx, mz + 1.5 * nz);
                                        if (dehors == soi) dehors = Lue(mx + 2.5 * nx, mz + 2.5 * nz);
                                        if (dehors == 0 || dehors > soi) vue = dehors;
                                    }
                                }
                                if (vue == voisine) continue;
                                if (voisine >= 0) morceaux.Add(new Morceau { Dedans = (ushort)soi, Dehors = (ushort)voisine,
                                    Ax = (float)(ax + dx * debut / bouts), Az = (float)(az + dz * debut / bouts), Bx = (float)(ax + dx * b / bouts), Bz = (float)(az + dz * b / bouts) });
                                voisine = vue; debut = b;
                            }
                        }
                    }
            }
            return morceaux.ToArray();
        }

        // Écrit dans un canal de `champ` (un octet tous les `saut`, à partir de `decalage`), pour chaque texel du
        // rectangle [i0, i1[ × [j0, j1[, la distance de son centre au plus proche morceau qui sépare son groupe d'un
        // autre, ou `AU_LOIN` à `portee` texels et plus. `groupes` range chaque numéro de texel dans un groupe ; un
        // groupe négatif n'a pas de bord et n'en fait pas. Chaque bande de lignes est à une seule tâche, qui y passe
        // tous les morceaux à sa portée : le résultat ne dépend pas de l'ordre des tâches.
        private static void Porter(ushort[] lieux, int largeur, Morceau[] morceaux, byte[] champ, int saut, int decalage, int[] groupes, double portee, int i0, int j0, int i1, int j1) {
            if (i1 <= i0 || j1 <= j0) return;
            var parBande = new List<int>[(j1 - j0 + BANDE - 1) / BANDE];
            for (int m = 0; m < morceaux.Length; m++) {
                Morceau c = morceaux[m]; int g1 = groupes[c.Dedans], g2 = groupes[c.Dehors];
                if (g1 == g2 || g1 < 0 || g2 < 0 || Math.Max(c.Ax, c.Bx) + portee < i0 || Math.Min(c.Ax, c.Bx) - portee > i1) continue;
                int bas = Math.Max(j0, (int)Math.Floor(Math.Min(c.Az, c.Bz) - portee - 0.5)), haut = Math.Min(j1 - 1, (int)Math.Ceiling(Math.Max(c.Az, c.Bz) + portee - 0.5));
                for (int b = (bas - j0) / BANDE; bas <= haut && b <= (haut - j0) / BANDE; b++) (parBande[b] ?? (parBande[b] = new List<int>())).Add(m);
            }
            double portee2 = portee * portee;
            Parallel.For(0, parBande.Length, b => {
                int debut = j0 + b * BANDE, fin = Math.Min(debut + BANDE, j1);
                for (int j = debut; j < fin; j++)
                    for (int i = i0; i < i1; i++) champ[(j * largeur + i) * saut + decalage] = AU_LOIN;
                if (parBande[b] == null) return;
                foreach (int m in parBande[b]) {
                    Morceau c = morceaux[m]; int g1 = groupes[c.Dedans], g2 = groupes[c.Dehors];
                    double dx = c.Bx - c.Ax, dz = c.Bz - c.Az, l2 = dx * dx + dz * dz, inv = l2 > 0 ? 1 / l2 : 0;
                    int ia = Math.Max(i0, (int)Math.Ceiling(Math.Min(c.Ax, c.Bx) - portee - 0.5)), ib = Math.Min(i1 - 1, (int)Math.Floor(Math.Max(c.Ax, c.Bx) + portee - 0.5));
                    int ja = Math.Max(debut, (int)Math.Ceiling(Math.Min(c.Az, c.Bz) - portee - 0.5)), jb = Math.Min(fin - 1, (int)Math.Floor(Math.Max(c.Az, c.Bz) + portee - 0.5));
                    for (int j = ja; j <= jb; j++) {
                        double pz = j + 0.5 - c.Az; int ligne = j * largeur;
                        for (int i = ia; i <= ib; i++) {
                            int g = groupes[lieux[ligne + i]]; if (g != g1 && g != g2) continue;
                            double px = i + 0.5 - c.Ax, t = Math.Min(Math.Max((px * dx + pz * dz) * inv, 0), 1);
                            double ex = px - t * dx, ez = pz - t * dz, d2 = ex * ex + ez * ez; if (d2 >= portee2) continue;
                            byte code = (byte)(255 * Math.Sqrt(Math.Sqrt(d2) / portee) + 0.5); int k = (ligne + i) * saut + decalage;
                            if (code < champ[k]) champ[k] = code;
                        }
                    }
                }
            });
        }

        // La mer hors de la carte n'est pas une côte : la terre ne plonge pas vers elle, et elle reste au ras de l'eau, sans fond.
        private static float[] Relief(ushort[] lieux, int largeur, int hauteur, double minX, double minZ, double pasDesLieux, float[] socles, float[] heurts, Enveloppe enveloppe, byte[] horsCarte) {
            int l = largeur / TEXELS_PAR_RELIEF, h = hauteur / TEXELS_PAR_RELIEF; double pas = pasDesLieux * TEXELS_PAR_RELIEF;
            // Chaque altitude résume ses texels de lieux : terre si la moitié l'est, socle et heurt moyens (la mer compte pour rien).
            var socle = new float[l * h]; var heurt = new float[l * h]; var terre = new bool[l * h]; var mer = new bool[l * h];
            float part = 1f / (TEXELS_PAR_RELIEF * TEXELS_PAR_RELIEF);
            Parallel.For(0, h, j => {
                for (int i = 0; i < l; i++) {
                    int aTerre = 0; float s = 0, e = 0;
                    for (int dj = 0; dj < TEXELS_PAR_RELIEF; dj++)
                        for (int di = 0; di < TEXELS_PAR_RELIEF; di++) {
                            ushort c = lieux[(j * TEXELS_PAR_RELIEF + dj) * largeur + i * TEXELS_PAR_RELIEF + di];
                            if (c == 0) continue;
                            aTerre++; s += socles[c - 1]; e += heurts[c - 1];
                        }
                    int k = j * l + i; socle[k] = s * part; heurt[k] = e * part; terre[k] = aTerre * 2 >= TEXELS_PAR_RELIEF * TEXELS_PAR_RELIEF; mer[k] = !terre[k];
                }
            });
            bool[] hors = HorsDeLaCarte(terre, l, h, minX, minZ, pas, enveloppe, horsCarte);
            for (int k = 0; k < mer.Length; k++) if (hors[k]) mer[k] = false;
            // Les classes se fondent d'une cellule à l'autre au lieu de dessiner des marches le long des bords.
            int rayon = Math.Max(1, (int)Math.Round(FLOU_KM / pas));
            Flouter(socle, l, h, rayon); Flouter(heurt, l, h, rayon);
            float[] versLaMer = Distances(mer, l, h, (float)pas), versLaTerre = Distances(terre, l, h, (float)pas);
            // Le fond, nul à terre, lissé pour que les lignes où deux rivages sont aussi loin ne se voient pas.
            var fond = new float[l * h];
            Parallel.For(0, h, j => { for (int i = 0; i < l; i++) { int k = j * l + i; if (!terre[k]) fond[k] = (float)(FOND * Plonge(versLaTerre[k] / LARGE_KM)); } });
            Flouter(fond, l, h, Math.Max(1, (int)Math.Round(FLOU_DE_MER_KM / pas)));
            var altitudes = new float[l * h];
            Parallel.For(0, h, j => {
                for (int i = 0; i < l; i++) {
                    int k = j * l + i;
                    if (hors[k]) { altitudes[k] = RIVAGE; continue; }
                    if (!terre[k]) { altitudes[k] = -fond[k]; continue; }
                    double brut = socle[k] + heurt[k] * (2 * Bruit(minX + (i + 0.5) * pas, minZ + (j + 0.5) * pas) - 1);
                    altitudes[k] = (float)Math.Min(Math.Max(RIVAGE + Lisse(versLaMer[k] / COTE_KM) * brut, RIVAGE), PLAFOND);
                }
            });
            return altitudes;
        }

        // De 0 à 1 sans cassure, 0 avant et 1 après.
        private static double Lisse(double t) { t = Math.Min(Math.Max(t, 0), 1); return t * t * (3 - 2 * t); }
        // De 0 à 1, d'abord vite puis de plus en plus doucement, 1 après.
        private static double Plonge(double t) { t = 1 - Math.Min(Math.Max(t, 0), 1); return 1 - t * t * t; }

        // Deux passes de moyenne glissante par axe ; au bord, la moyenne ne compte que ce qui existe.
        private static void Flouter(float[] valeurs, int l, int h, int rayon) {
            var tampon = new float[valeurs.Length];
            for (int passe = 0; passe < 2; passe++) {
                Parallel.For(0, h, j => { Glisser(valeurs, tampon, j * l, 1, l, rayon); });
                Parallel.For(0, l, i => { Glisser(tampon, valeurs, i, l, h, rayon); });
            }
        }
        private static void Glisser(float[] source, float[] cible, int debut, int saut, int nombre, int rayon) {
            double somme = 0; int compte = 0;
            for (int k = 0; k < Math.Min(rayon, nombre); k++) { somme += source[debut + k * saut]; compte++; }
            for (int k = 0; k < nombre; k++) {
                if (k + rayon < nombre) { somme += source[debut + (k + rayon) * saut]; compte++; }
                if (k - rayon - 1 >= 0) { somme -= source[debut + (k - rayon - 1) * saut]; compte--; }
                cible[debut + k * saut] = (float)(somme / compte);
            }
        }

        // La distance en km de chaque texel au plus proche texel marqué, par deux balayages (droit 1, diagonale √2).
        private static float[] Distances(bool[] marques, int l, int h, float pas) {
            const float LOIN = 1e9f; float droit = pas, biais = pas * 1.41421356f;
            var d = new float[marques.Length];
            for (int k = 0; k < d.Length; k++) d[k] = marques[k] ? 0f : LOIN;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < l; i++) {
                    int k = j * l + i; float m = d[k]; if (m == 0f) continue;
                    if (i > 0) m = Math.Min(m, d[k - 1] + droit);
                    if (j > 0) { m = Math.Min(m, d[k - l] + droit); if (i > 0) m = Math.Min(m, d[k - l - 1] + biais); if (i + 1 < l) m = Math.Min(m, d[k - l + 1] + biais); }
                    d[k] = m;
                }
            for (int j = h - 1; j >= 0; j--)
                for (int i = l - 1; i >= 0; i--) {
                    int k = j * l + i; float m = d[k]; if (m == 0f) continue;
                    if (i + 1 < l) m = Math.Min(m, d[k + 1] + droit);
                    if (j + 1 < h) { m = Math.Min(m, d[k + l] + droit); if (i + 1 < l) m = Math.Min(m, d[k + l + 1] + biais); if (i > 0) m = Math.Min(m, d[k + l - 1] + biais); }
                    d[k] = m;
                }
            return d;
        }

        // Un bruit à crêtes entre 0 et 1, le même pour le même point : cinq octaves sur un sol un peu tordu, pour que
        // les chaînes ne suivent pas la grille.
        private static double Bruit(double x, double z) {
            double tx = x + 18 * Onde(x / 90 + 11.3, z / 90 - 4.7), tz = z + 18 * Onde(x / 90 - 7.1, z / 90 + 3.9);
            double somme = 0, poids = 0, force = 1, frequence = 1 / 70.0;
            for (int octave = 0; octave < 5; octave++) {
                double crete = 1 - Math.Abs(Onde(tx * frequence, tz * frequence));
                somme += crete * crete * force; poids += force; force *= 0.5; frequence *= 2.1;
            }
            return somme / poids;
        }
        // Un bruit de gradient entre -1 et 1, nul aux nœuds de la grille entière, tiré d'un hachage d'entiers.
        private static double Onde(double x, double z) {
            double fx = Math.Floor(x), fz = Math.Floor(z); int ix = (int)fx, iz = (int)fz; double dx = x - fx, dz = z - fz;
            double u = dx * dx * dx * (dx * (dx * 6 - 15) + 10), v = dz * dz * dz * (dz * (dz * 6 - 15) + 10);
            double sud = Pente(ix, iz, dx, dz) + u * (Pente(ix + 1, iz, dx - 1, dz) - Pente(ix, iz, dx, dz));
            double nord = Pente(ix, iz + 1, dx, dz - 1) + u * (Pente(ix + 1, iz + 1, dx - 1, dz - 1) - Pente(ix, iz + 1, dx, dz - 1));
            return sud + v * (nord - sud);
        }
        private static double Pente(int ix, int iz, double dx, double dz) {
            uint h = unchecked((uint)ix * 0x9E3779B1u ^ (uint)iz * 0x85EBCA77u);
            h ^= h >> 15; h = unchecked(h * 0x2C1B3C6Du); h ^= h >> 12; h = unchecked(h * 0x297A2D39u); h ^= h >> 15;
            switch (h & 7) {
                case 0: return dx + dz; case 1: return dx - dz; case 2: return dz - dx; case 3: return -dx - dz;
                case 4: return dx * 1.41421356; case 5: return -dx * 1.41421356; case 6: return dz * 1.41421356; default: return -dz * 1.41421356;
            }
        }
    }
}
