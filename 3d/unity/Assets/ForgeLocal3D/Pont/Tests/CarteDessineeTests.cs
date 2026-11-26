using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont.Tests {
    // La carte servie se pose en un terrain d'un seul tenant, levé de la carte et de la forme de ses lieux, où chaque
    // lieu a sa teinte, au départ la couleur de la puissance de sa cellule ; sans carte, le message et rien d'autre ;
    // sans formes, la carte dit pourquoi elle ne se dessine pas. L'attendu vient de la fixture, lue par ClientCarte :
    // les couleurs par Mailler, le terrain par celui que la carte expose. La carte entière se sert avec des formes d'un
    // lieu par cellule, tirées de ses contours ; les lieux eux-mêmes se jugent sur les réponses figées de l'Ouest.
    public sealed class CarteDessineeTests {
        private const int DELAI_MAX_PAS_MS = 100, ATTENTE_LECTURE_MS = 20000, LENTEUR_MS = 2000;
        private int port, requetes; private volatile string chemin; private volatile int statutDesFormes; private volatile byte[] formes;
        private HttpListener ecoute; private Thread fil; private GameObject objet; private CarteDessinee carte;
        private static byte[] Fixture => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
        private static byte[] formesDuFixture; // les formes d'un lieu par cellule de la fixture, tirées une fois
        private static byte[] FormesDuFixture => formesDuFixture ?? (formesDuFixture = FormesDeTest.UnLieuParCelluleServi(Fixture));
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); requetes = 0; chemin = null; statutDesFormes = 200; formes = FormesDuFixture;
        }
        [TearDown] public void Fermer() {
            if (carte != null) carte.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet);
            ecoute?.Close(); ecoute = null; fil?.Join(TimeSpan.FromSeconds(5)); fil = null;
        }
        // Rend toujours la même réponse à `/carte`, et `formes` à `/formes` avec `statutDesFormes`, `lenteur` ms après
        // avoir compté la requête.
        private void Servir(int lenteur, int statut, byte[] carteServie) {
            ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            HttpListener auditeur = ecoute;
            fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext();
                    chemin = ctx.Request.Url.PathAndQuery; Interlocked.Increment(ref requetes); Thread.Sleep(lenteur);
                    bool desLieux = ctx.Request.Url.AbsolutePath == "/formes"; byte[] octets = desLieux ? formes : carteServie;
                    ctx.Response.StatusCode = desLieux ? statutDesFormes : statut; ctx.Response.ContentLength64 = octets.Length;
                    ctx.Response.OutputStream.Write(octets, 0, octets.Length); ctx.Response.Close();
                } } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
        }
        // L'attendu, lu au faux service avant de poser le composant ; le compteur repart ensuite de zéro.
        private CarteMaillee Attendue(out int servies) {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Interlocked.Exchange(ref requetes, 0); servies = lecture.Carte.Cellules.Count;
            return MaillageDeCarte.Mailler(lecture.Carte);
        }
        private void Poser() { objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.Demarrer(); }
        private int TerrainsSousLaCarte => objet.GetComponentsInChildren<MeshFilter>(true).Length; // toutes racines confondues : une double pose se voit
        private Material Matiere => objet.transform.Find(CarteDessinee.TERRAIN).GetComponent<MeshRenderer>().sharedMaterial;
        // La teinte versée au shader pour le lieu de ce numéro : la case lieu + 1 de la palette, la case 0 étant la mer.
        // Sur la carte entière, d'un lieu par cellule, le lieu d'une cellule a le numéro de son rang servi.
        private Color32 Versee(int lieu) { var palette = (Texture2D)Matiere.GetTexture("_Palette"); return palette.GetPixel((lieu + 1) % palette.width, (lieu + 1) / palette.width); }
        // À un cran près par canal : la palette garde huit bits par canal.
        private static bool Proches(Color32 a, Color32 b) => Math.Abs(a.r - b.r) <= 1 && Math.Abs(a.g - b.g) <= 1 && Math.Abs(a.b - b.b) <= 1 && Math.Abs(a.a - b.a) <= 1;
        // Une terre carrée de 10 km, sans puissance ni ville, son coin sud-ouest en (x, 0).
        private static CelluleDeCarte Carre(long id, double x) {
            var anneau = new[] { new PointCarte(x, 0), new PointCarte(x + 10000, 0), new PointCarte(x + 10000, 10000), new PointCarte(x, 10000), new PointCarte(x, 0) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]);
        }
        // Une lecture complète : le pas la lance, elle finit hors du fil, un pas au même instant l'applique.
        private void Lire(double instant) {
            carte.Pas(instant); var montre = Stopwatch.StartNew();
            while (carte.LectureEnVol && montre.ElapsedMilliseconds < ATTENTE_LECTURE_MS) Thread.Sleep(10);
            Assert.IsFalse(carte.LectureEnVol, "la lecture n'a pas fini"); carte.Pas(instant);
        }
        private void Absence(string cause) {
            string[] l = carte.TexteAffiche.Split('\n'); Text texte = objet.GetComponentInChildren<Text>();
            Assert.IsTrue(carte.CellulesPosees == 0 && carte.CellulesServies == -1, carte.TexteAffiche);
            Assert.AreEqual(CarteDessinee.MESSAGE_ABSENCE, l[0]); StringAssert.Contains(cause, l[1]);
            Assert.IsTrue(texte != null && texte.gameObject.activeInHierarchy && texte.text == carte.TexteAffiche);
        }
        [Test] public void La_carte_servie_pose_un_terrain_ou_chaque_cellule_servie_a_sa_teinte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser();
            Lire(1);
            Assert.IsTrue(Volatile.Read(ref requetes) == 2 && chemin == "/formes", requetes + " requêtes, la dernière " + chemin);
            Assert.IsTrue(servies == 596 && attendue.Cellules.Count == servies && carte.CellulesServies == servies && carte.CellulesPosees == servies && TerrainsSousLaCarte == 1, carte.CellulesPosees + " posées, " + TerrainsSousLaCarte + " terrain(s)");
            Transform sol = objet.transform.Find(CarteDessinee.TERRAIN); Assert.IsNotNull(sol, "le terrain n'est pas un enfant direct de la carte");
            TerrainDeCarte terrain = carte.Terrain; Assert.IsNotNull(terrain, "la carte posée n'expose pas son terrain");
            // Le maillage posé est celui du terrain levé, sommet pour sommet, et il reste sous le plan des calques.
            Mesh m = sol.GetComponent<MeshFilter>().sharedMesh; Vector3[] s = m.vertices; int[] t = m.triangles; Vector2[] uv = m.uv;
            Assert.IsTrue(s.Length == terrain.Sommets.Count && uv.Length == terrain.Uv.Count && t.Length == terrain.Triangles.Count && t.Length > 0, s.Length + " sommets, " + t.Length + " indices");
            int ecarts = 0;
            for (int k = 0; k < s.Length; k++) if (!Egal(s[k], terrain.Sommets[k]) || uv[k].x != terrain.Uv[k].x || uv[k].y != terrain.Uv[k].y) ecarts++;
            for (int k = 0; k < t.Length; k++) if (t[k] != terrain.Triangles[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "sommets ou triangles différents du terrain levé");
            Assert.LessOrEqual(m.bounds.max.y, 0f, "une cime dépasse le plan des calques");
            // Un seul matériau, au shader du relief, qui reçoit les grilles du terrain, ses distances aux traits, les tables des pays et ses bornes.
            MeshRenderer rendu = sol.GetComponent<MeshRenderer>(); Material mat = rendu.sharedMaterial;
            Assert.IsTrue(rendu.sharedMaterials.Length == 1 && mat.shader.name == CarteDessinee.SHADER_DU_TERRAIN, mat.shader.name);
            Texture lieux = mat.GetTexture("_Lieux"), relief = mat.GetTexture("_Relief"); var palette = mat.GetTexture("_Palette") as Texture2D;
            Assert.IsTrue(lieux != null && lieux.width == terrain.Largeur && lieux.height == terrain.Hauteur && lieux.filterMode == FilterMode.Point, "la grille des lieux n'est pas celle du terrain");
            Assert.IsTrue(relief != null && relief.width == terrain.LargeurDuRelief && relief.height == terrain.HauteurDuRelief, "la grille du relief n'est pas celle du terrain");
            Assert.IsTrue(palette != null && palette.width * palette.height > terrain.NombreDeLieux && terrain.NombreDeLieux == servies && palette.filterMode == FilterMode.Point, "la palette n'a pas une case par lieu, plus la mer");
            Assert.AreEqual(0, ((Color32)palette.GetPixel(0, 0)).a, "la case de la mer a une teinte");
            Assert.IsTrue(mat.GetFloat("_PasDuRelief") == terrain.PasDuRelief && mat.GetFloat("_Fond") == TerrainDeCarte.FOND && mat.GetFloat("_Plafond") == TerrainDeCarte.PLAFOND, "le shader n'a pas les bornes du terrain");
            Texture bords = mat.GetTexture("_Bords"), frontieres = mat.GetTexture("_Frontieres"), desPays = mat.GetTexture("_Pays"), teintesDesPays = mat.GetTexture("_TeintesDesPays");
            Assert.IsTrue(bords != null && bords.width == terrain.Largeur && bords.height == terrain.Hauteur && bords.filterMode == FilterMode.Point, "les distances aux bords n'ont pas un texel par texel du terrain");
            Assert.IsTrue(frontieres != null && frontieres.width == terrain.Largeur && frontieres.height == terrain.Hauteur && frontieres.filterMode == FilterMode.Point, "les distances aux frontières n'ont pas un texel par texel du terrain");
            Assert.IsTrue(desPays != null && desPays.width == palette.width && desPays.height == palette.height && desPays.filterMode == FilterMode.Point, "la table des pays n'a pas une case par case de la palette");
            Assert.IsTrue(teintesDesPays != null && teintesDesPays.width == palette.width && teintesDesPays.height == palette.height && teintesDesPays.filterMode == FilterMode.Point, "la table des liserés n'a pas la taille de la palette");
            Assert.IsTrue(mat.GetFloat("_Pas") == terrain.Pas && mat.GetFloat("_PorteeDesBords") == TerrainDeCarte.PORTEE_DES_BORDS_KM && mat.GetFloat("_PorteeDesFrontieres") == TerrainDeCarte.PORTEE_DES_FRONTIERES_KM, "le shader n'a pas le pas du terrain ni les portées de ses distances");
            // Chaque cellule servie a la couleur de sa puissance, lue par son numéro et versée à son rang.
            var couleurs = new HashSet<Color>(); int fausses = 0, sansPuissance = 0, avecPuissance = 0, malRattachees = 0;
            for (int i = 0; i < servies; i++) {
                MaillageDeCellule c = attendue.Cellules[i]; Color? teinte = carte.TeinteDe(c.CellId);
                Assert.IsTrue(teinte.HasValue, "cellule " + c.CellId + " sans teinte"); Assert.AreEqual((Color32)c.Couleur, (Color32)teinte.Value, "cellule " + c.CellId);
                if (!Proches(Versee(i), c.Couleur)) fausses++; couleurs.Add(c.Couleur);
                CelluleDeCarte servie = carte.Lue.Cellules[i]; string pays = carte.PaysDe(c.CellId);
                if (servie.CellId != c.CellId) malRattachees++;
                else if (servie.Puissance == null) { sansPuissance++; if (pays != null) malRattachees++; }
                else { avecPuissance++; if (pays != "puissance " + servie.Puissance.Id) malRattachees++; }
            }
            Assert.AreEqual(0, fausses, "teintes versées différentes des couleurs attendues");
            Assert.AreEqual(40, couleurs.Count, "couleurs de puissance");
            // À la pose, chaque cellule est au pays de sa puissance servie ; sans puissance, à aucun.
            Assert.IsTrue(sansPuissance == 31 && avecPuissance == 565 && malRattachees == 0, sansPuissance + " sans puissance, " + avecPuissance + " avec, " + malRattachees + " mal rattachées");
            // Les frontières se mesurent sur ce rattachement : à terre, des points en sont proches et d'autres hors de portée ; en mer, aucune.
            int pres = 0, loin = 0, enMer = 0, merMesuree = 0;
            for (int j = 8; j < terrain.Hauteur; j += 16)
                for (int i = 8; i < terrain.Largeur; i += 16) {
                    float x = terrain.Coin.x + (i + .5f) * terrain.Pas, z = terrain.Coin.y + (j + .5f) * terrain.Pas, d = carte.DistanceALaFrontiere(x, z);
                    if (terrain.CelluleEn(x, z) == 0) { enMer++; if (d != TerrainDeCarte.PORTEE_DES_FRONTIERES_KM) merMesuree++; }
                    else if (d < 2f) pres++; else if (d == TerrainDeCarte.PORTEE_DES_FRONTIERES_KM) loin++;
                }
            TestContext.Out.WriteLine(pres + " points à moins de 2 km d'une frontière, " + loin + " hors de portée, " + enMer + " en mer");
            Assert.IsTrue(pres > 100 && loin > 100 && enMer > 1000, pres + " près d'une frontière, " + loin + " hors de portée, " + enMer + " en mer : l'échantillon ne juge rien");
            Assert.AreEqual(0, merMesuree, "une frontière est mesurée en mer");
            Assert.IsTrue(carte.TexteAffiche == "" && !objet.GetComponentInChildren<Text>(true).gameObject.activeSelf);
            for (int i = 1; i <= 20; i++) { carte.Pas(1 + 10 * i); Assert.IsFalse(carte.LectureEnVol); }
            Assert.IsTrue(Volatile.Read(ref requetes) == 2 && carte.CellulesPosees == servies && TerrainsSousLaCarte == 1 && carte.Terrain == terrain, TerrainsSousLaCarte + " terrain(s)");
        }
        // Une vue change la teinte d'une cellule par son numéro, sans toucher à sa voisine ; une cellule retirée rend la mer.
        [Test] public void Une_cellule_se_reteint_et_se_retire_par_son_numero() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser();
            long une = lue.Cellules[3].CellId, voisine = lue.Cellules[4].CellId; var neuve = new Color(0.2f, 0.4f, 0.6f, 0.3f); var opaque = new Color(0.2f, 0.4f, 0.6f, 1f);
            Assert.IsTrue(carte.TeinteDe(une) == null && !carte.Teinter(une, neuve) && !carte.Retirer(une), "une teinte avant la pose");
            Lire(1);
            Color avant = carte.TeinteDe(une).Value, celleDeLaVoisine = carte.TeinteDe(voisine).Value;
            Assert.IsTrue(Proches(Versee(3), avant) && !Proches(avant, opaque), "la teinte de départ n'est pas versée, ou c'est déjà la neuve");
            Assert.IsTrue(carte.TeinteDe(-5) == null && !carte.Teinter(-5, neuve) && !carte.Retirer(-5), "une cellule que le service ne sert pas a une teinte");
            Assert.IsTrue(carte.Teinter(une, neuve)); Assert.AreEqual((Color32)opaque, (Color32)carte.TeinteDe(une).Value, "une teinte se garde opaque");
            carte.Pas(2);
            Assert.IsTrue(Proches(Versee(3), opaque), "la teinte neuve n'est pas versée au shader");
            Assert.IsTrue(Proches(Versee(4), celleDeLaVoisine) && carte.TeinteDe(voisine) == celleDeLaVoisine, "la voisine a changé de teinte");
            Assert.IsTrue(carte.Retirer(une) && carte.CellulesPosees == 595 && carte.CellulesServies == 596, carte.CellulesPosees + " posées");
            Assert.IsTrue(carte.TeinteDe(une) == null && !carte.Teinter(une, neuve) && !carte.Retirer(une), "une cellule retirée se reteint ou se retire encore");
            carte.Pas(3);
            Assert.AreEqual(0, Versee(3).a, "une cellule retirée garde une teinte : son sol ne rend pas la mer");
            Assert.IsTrue(Proches(Versee(4), celleDeLaVoisine) && carte.CellulesPosees == 595);
        }
        // Les distances à la marque, en km, de chaque texel de la zone d'une cellule élargie de `marge` texels, avec la cellule de chaque texel.
        private List<(float distance, int cellule)> AutourDe(int rang, int marge) {
            TerrainDeCarte t = carte.Terrain; RectInt z = t.ZoneDe(rang); var vus = new List<(float, int)>();
            for (int j = Math.Max(0, z.yMin - marge); j < Math.Min(t.Hauteur, z.yMax + marge); j++)
                for (int i = Math.Max(0, z.xMin - marge); i < Math.Min(t.Largeur, z.xMax + marge); i++) {
                    float x = t.Coin.x + (i + .5f) * t.Pas, y = t.Coin.y + (j + .5f) * t.Pas; vus.Add((carte.DistanceALaMarque(x, y), t.CelluleEn(x, y) - 1));
                }
            return vus;
        }
        // La marque cerne une seule cellule à la fois d'un trait tiré de ses côtés, côte comprise ; elle ne touche ni à sa
        // teinte ni à la palette, et la grille du trait revient au loin quand elle part.
        [Test] public void La_marque_cerne_une_cellule_sans_toucher_a_la_palette() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser();
            long une = lue.Cellules[10].CellId, autre = lue.Cellules[300].CellId; var rouge = new Color(0.9f, 0.1f, 0.1f, 0.5f); var bleu = new Color(0.1f, 0.1f, 0.9f, 1f);
            Assert.IsTrue(!carte.Marquer(une, rouge) && carte.Marquee == null && carte.DistanceALaMarque(0, 0) == -1f, "une marque avant la pose");
            Lire(1); TerrainDeCarte t = carte.Terrain; float portee = TerrainDeCarte.PORTEE_DE_LA_MARQUE_KM; int marge = Mathf.CeilToInt(portee / t.Pas) + 2;
            Color teinte = carte.TeinteDe(une).Value, teinteDeLAutre = carte.TeinteDe(autre).Value; Assert.IsNull(carte.Marquee);
            Assert.IsTrue(AutourDe(10, marge).All(v => v.distance == portee), "sans marque, une distance à la marque est mesurée");
            Assert.IsTrue(carte.Marquer(une, rouge) && carte.Marquee == une); carte.Pas(2);
            Assert.IsTrue(Proches(Versee(10), teinte) && Proches(Versee(20), carte.TeinteDe(lue.Cellules[20].CellId).Value), "la marque a touché la palette");
            Assert.AreEqual(new Vector4(t.PremierLieuDe(10) + 1, t.PremierLieuDe(10) + t.LieuxDe(10), 0, 0), Matiere.GetVector("_LieuxMarques"), "le shader ne sait pas quels lieux cerner");
            Assert.IsTrue(Proches(Matiere.GetColor("_CouleurDeLaMarque"), new Color(0.9f, 0.1f, 0.1f, 1f)), "le trait n'a pas la couleur de la marque, opaque");
            // Près du trait : des texels de la cellule et de la mer qui la borde ; plus loin, la portée.
            var autour = AutourDe(10, marge); int dedans = autour.Count(v => v.distance < 1f && v.cellule == 10), enMer = autour.Count(v => v.distance < 1f && v.cellule == -1);
            Assert.IsTrue(dedans > 5 && enMer > 5, dedans + " texels de la cellule et " + enMer + " de mer près du trait : la côte n'est pas cernée");
            Assert.IsTrue(autour.Any(v => v.distance == portee), "échantillon vide : tout est près du trait");
            Assert.IsTrue(AutourDe(300, marge).All(v => v.distance == portee), "une cellule lointaine a une distance à la marque");
            Assert.IsTrue(carte.Marquer(autre, bleu) && carte.Marquee == autre); carte.Pas(3);
            Assert.IsTrue(AutourDe(10, marge).All(v => v.distance == portee), "la cellule d'avant garde le trait : deux marques à la fois");
            Assert.IsTrue(AutourDe(300, marge).Any(v => v.distance < 1f && v.cellule == 300), "la cellule neuve n'est pas cernée");
            Assert.IsTrue(!carte.Marquer(-5, rouge) && carte.Marquee == autre, "un refus a fait tomber la marque d'avant");
            Assert.IsTrue(Proches(Versee(300), teinteDeLAutre), "la marque a couvert la teinte de la cellule");
            carte.Demarquer(); Assert.IsNull(carte.Marquee); carte.Pas(5);
            Assert.IsTrue(AutourDe(300, marge).All(v => v.distance == portee) && Matiere.GetVector("_LieuxMarques").x == -1f, "la marque partie laisse son trait");
            // Une cellule retirée perd sa marque : la mer ne se marque pas.
            Assert.IsTrue(carte.Marquer(une, rouge) && carte.Retirer(une) && carte.Marquee == null && !carte.Marquer(une, rouge), "une cellule retirée reste marquée"); carte.Pas(6);
            Assert.IsTrue(AutourDe(10, marge).All(v => v.distance == portee), "la marque d'une cellule retirée se dessine encore");
        }
        // Un éclat couvre la teinte d'autant de cellules qu'on veut, sans la changer, à l'opacité qui le dit au shader ; la
        // marque, un trait, ne le touche pas.
        [Test] public void Un_eclat_couvre_des_cellules_sans_changer_leur_teinte_et_la_marque_ne_le_touche_pas() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser();
            long une = lue.Cellules[10].CellId, autre = lue.Cellules[20].CellId; var or = new Color(0.8f, 0.6f, 0.2f, 0.4f); var orOpaque = new Color(0.8f, 0.6f, 0.2f, 1f); var rouge = new Color(0.9f, 0.1f, 0.1f, 1f);
            var orVerse = new Color(0.8f, 0.6f, 0.2f, CarteDessinee.OPACITE_D_ECLAT);
            Assert.IsTrue(!carte.Eclairer(une, or) && carte.EclatDe(une) == null, "un éclat avant la pose");
            Lire(1); Color teinte = carte.TeinteDe(une).Value, teinteDeLAutre = carte.TeinteDe(autre).Value; int maillages = objet.GetComponentsInChildren<MeshFilter>(true).Length;
            Assert.IsTrue(carte.Eclairer(une, or) && carte.Eclairer(autre, or) && !carte.Eclairer(-5, or)); carte.Pas(2);
            Assert.IsTrue(Proches(Versee(10), orVerse) && Proches(Versee(20), orVerse), "deux cellules éclairées ne sont pas versées à la couleur de l'éclat, moins opaque qu'une teinte");
            Assert.IsTrue(carte.TeinteDe(une) == teinte && carte.TeinteDe(autre) == teinteDeLAutre && carte.EclatDe(une) == orOpaque && carte.EclatDe(lue.Cellules[30].CellId) == null, "l'éclat a changé une teinte, ou ne se relit pas");
            Assert.AreEqual(maillages, objet.GetComponentsInChildren<MeshFilter>(true).Length, "un éclat pose un maillage au-dessus du terrain");
            Assert.IsTrue(carte.Marquer(une, rouge)); carte.Pas(3); Assert.IsTrue(Proches(Versee(10), orVerse) && Proches(Versee(20), orVerse), "la marque a touché l'éclat");
            carte.Demarquer(); carte.Pas(4); Assert.IsTrue(Proches(Versee(10), orVerse), "l'éclat ne reste pas quand la marque part");
            carte.Eteindre(une); carte.Pas(5); Assert.IsTrue(Proches(Versee(10), teinte) && Proches(Versee(20), orVerse) && carte.EclatDe(une) == null, "l'éclat éteint ne rend pas la teinte, ou éteint l'autre");
            Assert.IsTrue(carte.Retirer(autre) && carte.EclatDe(autre) == null && !carte.Eclairer(autre, or), "une cellule retirée reste éclairée"); carte.Pas(6);
            Assert.AreEqual(0, Versee(20).a, "l'éclat d'une cellule retirée se dessine encore");
        }
        // Les bornes de la vue : la boîte des cellules, élargie d'une marge de mer, toute dans le terrain levé. Rien ne s'y
        // dessine : ni table, ni filet ; au bord, la mer continue.
        [Test] public void Les_bornes_de_la_vue_tiennent_dans_le_terrain_et_rien_ne_les_dessine() {
            Servir(0, 200, Fixture); Lue(out PointCarte o); Poser(); Assert.AreEqual(new Rect(), carte.Cadre, "des bornes avant la pose");
            Lire(1); TerrainDeCarte t = carte.Terrain; Bounds cellules = t.Boite; float marge = CarteDessinee.MARGE_DU_CADRE_KM; Rect cadre = carte.Cadre;
            Assert.IsTrue(Mathf.Abs(cadre.xMin - (cellules.min.x - marge)) < 1e-3f && Mathf.Abs(cadre.yMin - (cellules.min.z - marge)) < 1e-3f && Mathf.Abs(cadre.xMax - (cellules.max.x + marge)) < 1e-3f && Mathf.Abs(cadre.yMax - (cellules.max.z + marge)) < 1e-3f, "les bornes ne sont pas à leur marge des cellules : " + cadre);
            Assert.IsTrue(cadre.xMin > t.Coin.x && cadre.yMin > t.Coin.y && cadre.xMax < t.Coin.x + t.Largeur * t.Pas && cadre.yMax < t.Coin.y + t.Hauteur * t.Pas, "les bornes de la vue sortent du terrain : la vue montrerait le vide");
            foreach (string disparue in new[] { "_Table", "_Filet", "_Cadre" }) Assert.IsFalse(Matiere.HasProperty(disparue), "le terrain dessine encore " + disparue);
            // Glissé au loin, le point visé s'arrête au coin des bornes ; au plus loin, il revient au milieu de la carte.
            carte.Vue.Zoomer(10, new Vector2(.5f, .5f)); carte.Vue.Glisser(new Vector2(-1e7f, -1e7f), 900f);
            Assert.Less((carte.Vue.Vise - cadre.max).magnitude, 1e-2f, "glissé au nord-est, le point visé n'est pas au coin des bornes : " + carte.Vue.Vise);
            carte.Vue.Zoomer(-1000, new Vector2(.5f, .5f));
            Assert.Less((carte.Vue.Vise - cadre.center).magnitude, 1e-2f, "au plus loin, le point visé n'est pas au milieu des bornes : " + carte.Vue.Vise);
        }
        // Une image rendue par la caméra de la carte, en couleurs franches : au-delà de la coupe la plus à l'est (l'Anatolie),
        // le papier ; teinte par l'altitude, la terre prend la teinte des paliers. Au large de Lisbonne, aucun papier.
        [Test] public void L_image_montre_la_teinte_d_altitude_et_le_papier_hors_carte() {
            Servir(0, 200, Fixture); Lue(out PointCarte o); Poser(); Lire(1);
            TerrainDeCarte t = carte.Terrain; Vector4 coupe = t.Coupes.OrderByDescending(c => c.x + c.z).First();
            const int L = 800, H = 450; var ecran = new RenderTexture(L, H, 24); Camera cam = carte.camera; cam.targetTexture = ecran; cam.aspect = (float)L / H;
            try {
                var mer = new Color(0f, 0f, .5f, 1f); carte.Habiller(mer, mer, Color.white); carte.PeindreHorsCarte(new Color(1f, 0f, 1f, 1f));
                int Compter(Func<Color, bool> quoi) {
                    carte.Pas(2); cam.Render(); var lu = new Texture2D(L, H, TextureFormat.RGBA32, false); RenderTexture.active = ecran;
                    try { lu.ReadPixels(new Rect(0, 0, L, H), 0, 0); lu.Apply(); return lu.GetPixels().Count(quoi); }
                    finally { RenderTexture.active = null; UnityEngine.Object.DestroyImmediate(lu); }
                }
                bool Papier(Color c) => c.r > .4f && c.b > .4f && c.g < .25f;
                bool Vert(Color c) => c.g > .3f && c.r < .2f && c.b < .2f;
                carte.Vue.Changer(cam.aspect); carte.Vue.Centrer(new Vector2((coupe.x + coupe.z) / 2f, (coupe.y + coupe.w) / 2f), 200f);
                int papier = Compter(Papier), vertAvant = Compter(Vert);
                Assert.Greater(papier, L * H / 20, "au-delà de la coupe de l'Anatolie, le papier ne se voit pas : " + papier + " pixels");
                carte.TeindreParLAltitude(Enumerable.Repeat(new Color(0f, .9f, 0f, 1f), TerrainDeCarte.PALIERS.Count).ToArray());
                int vert = Compter(Vert);
                Assert.Greater(vert, L * H / 20, "teinte par l'altitude, la terre n'a pas la teinte des paliers : " + vert + " pixels");
                Assert.Less(vertAvant, vert / 10, "contre-épreuve : la terre avait déjà la teinte des paliers avant d'être teinte par l'altitude");
                // Contre-épreuve : au large de Lisbonne, la mer et le rivage, sans papier.
                Vector2 lisbonne = new Vector2((float)((2670000 - o.X) / 1000), (float)((1940000 - o.Y) / 1000)); carte.Vue.Centrer(lisbonne, 200f);
                Assert.AreEqual(0, Compter(Papier), "au large de Lisbonne, la mer se peint en papier");
            } finally { cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(ecran); }
        }
        // Teinte d'altitude, liseré, papier hors carte : des réglages du terrain, donnés avant ou après la pose.
        [Test] public void Les_modes_du_terrain_se_reglent_avant_comme_apres_la_pose() {
            Servir(0, 200, Fixture); Lue(out PointCarte o); Poser();
            var paliers = new[] { Color.blue, Color.green, Color.yellow, Color.red, Color.white };
            carte.TeindreParLAltitude(paliers); carte.MontrerLesLiseres(false); carte.PeindreHorsCarte(new Color(.9f, .8f, .7f, .2f));
            Assert.Throws<ArgumentException>(() => carte.TeindreParLAltitude(new[] { Color.red }), "une teinte par palier n'est pas exigée");
            Lire(1);
            Assert.IsTrue(carte.ParAltitude && Matiere.GetFloat("_ParAltitude") == 1f && Matiere.GetFloat("_ForceDesLiseres") == 0f && !carte.LiseresMontres, "un réglage donné avant la pose est perdu");
            for (int p = 0; p < paliers.Length; p++) Assert.IsTrue(Proches(Matiere.GetColor("_Palier" + p), paliers[p]), "palier " + p);
            var socles = TerrainDeCarte.PALIERS; Assert.AreEqual(new Vector4(socles[0].socle, socles[1].socle, socles[2].socle, socles[3].socle), Matiere.GetVector("_Socles"));
            Assert.AreEqual(socles[4].socle, Matiere.GetFloat("_DernierSocle")); Assert.IsTrue(Proches(Matiere.GetColor("_Papier"), new Color(.9f, .8f, .7f, 1f)), "le papier n'est pas versé, opaque");
            Texture horsCarte = Matiere.GetTexture("_HorsCarte"); Assert.IsTrue(horsCarte != null && horsCarte.width == carte.Terrain.LargeurDuRelief && horsCarte.height == carte.Terrain.HauteurDuRelief, "la mer hors carte n'a pas la grille du relief");
            carte.TeindreParLAltitude(null); carte.MontrerLesLiseres(true);
            Assert.IsTrue(!carte.ParAltitude && Matiere.GetFloat("_ParAltitude") == 0f && Matiere.GetFloat("_ForceDesLiseres") == 1f && carte.PaysMontres, "les teintes des lieux et le liseré ne reviennent pas");
        }
        // L'habillage donné avant la pose est celui du terrain qui naît ; donné après, il change le terrain posé.
        [Test] public void L_habillage_change_la_mer_le_rivage_et_les_cimes() {
            Servir(0, 200, Fixture); Attendue(out int servies); Poser();
            Color mer = new Color(0.1f, 0.2f, 0.3f, 1f), rivage = new Color(0.4f, 0.5f, 0.6f, 1f), cimes = new Color(0.7f, 0.8f, 0.9f, 1f);
            carte.Habiller(mer, rivage, cimes); Lire(1);
            Material mat = Matiere;
            Assert.IsTrue(mat.GetColor("_Mer") == mer && mat.GetColor("_Rivage") == rivage && mat.GetColor("_Roche") == cimes, "l'habillage donné avant la pose est perdu : " + mat.GetColor("_Mer"));
            carte.Habiller(cimes, mer, rivage);
            Assert.IsTrue(Matiere == mat && mat.GetColor("_Mer") == cimes && mat.GetColor("_Rivage") == mer && mat.GetColor("_Roche") == rivage, "l'habillage ne change pas le terrain posé : " + mat.GetColor("_Mer"));
            Assert.IsTrue(carte.CellulesPosees == servies && TerrainsSousLaCarte == 1);
        }
        // Une carte déjà lue se pose sans service ni caméra : le terrain se lève sur place, une seule fois.
        [Test] public void Une_carte_deja_lue_se_pose_sans_service() {
            objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>();
            Assert.IsTrue(carte.CellulesServies == -1 && carte.CellulesPosees == 0 && carte.Terrain == null && carte.Lue == null && carte.Origine == null && TerrainsSousLaCarte == 0, "une carte avant la pose");
            var lue = new CarteLue(2, new[] { Carre(7, 0), Carre(8, 10000) }); carte.Montrer(lue, FormesDeTest.UnLieuParCellule(lue));
            Assert.IsTrue(carte.CellulesServies == 2 && carte.CellulesPosees == 2 && carte.Terrain != null && carte.Lue == lue && carte.Formes != null && TerrainsSousLaCarte == 1, carte.CellulesPosees + " posées, " + TerrainsSousLaCarte + " terrain(s)");
            Assert.IsTrue(carte.Origine.HasValue && carte.Origine.Value.X == 10000 && carte.Origine.Value.Y == 5000, "l'origine n'est pas le centre des deux terres");
            Assert.IsTrue(carte.TexteAffiche == null && carte.Vue == null && carte.camera == null && !carte.LectureEnVol, "une carte montrée a créé une caméra, un texte ou une lecture");
            Assert.AreEqual((Color32)MaillageDeCarte.CouleurSansPuissance, (Color32)carte.TeinteDe(7).Value); Assert.IsTrue(Proches(Versee(0), MaillageDeCarte.CouleurSansPuissance) && Proches(Versee(1), MaillageDeCarte.CouleurSansPuissance));
            Assert.IsTrue(carte.CelluleSous(new Vector3(-5, 0, 0)).CellId == 7 && carte.CelluleSous(new Vector3(5, 0, 0)).CellId == 8 && carte.CelluleSous(new Vector3(50, 0, 0)) == null, "les terres ne sont pas où la carte les dessine");
            Assert.IsTrue(carte.Terrain.CelluleEn(-5, 0) == 1 && carte.Terrain.CelluleEn(5, 0) == 2 && carte.Terrain.CelluleEn(50, 0) == 0, "le terrain ne porte pas les terres à leur rang");
            TerrainDeCarte terrain = carte.Terrain; var seconde = new CarteLue(1, new[] { Carre(9, 0) }); carte.Montrer(seconde, FormesDeTest.UnLieuParCellule(seconde));
            Assert.IsTrue(carte.Terrain == terrain && carte.CellulesServies == 2 && TerrainsSousLaCarte == 1 && carte.TeinteDe(9) == null, "une seconde carte a remplacé la première");
        }
        // Verse au shader ce qui a changé, comme le fait chaque image du jeu.
        private void Verser() => typeof(CarteDessinee).GetMethod("LateUpdate", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(carte, null);
        // L'indice de pays versé au shader pour le lieu de ce numéro, et la couleur de liseré versée à cet indice.
        private int PaysVerse(int lieu) { var table = (Texture2D)Matiere.GetTexture("_Pays"); return Mathf.RoundToInt(table.GetPixel((lieu + 1) % table.width, (lieu + 1) / table.width).r * 65535f); }
        private Color32 LisereVerse(int indice) { var table = (Texture2D)Matiere.GetTexture("_TeintesDesPays"); return table.GetPixel(indice % table.width, indice / table.width); }
        // Deux terres de 10 km accolées, 7 à l'ouest et 8 à l'est : leur côté commun est en x = 0, la terre va de
        // z = -5 à z = 5, et les centres des texels d'un km tombent sur les demi-entiers.
        [Test] public void La_frontiere_suit_le_pays_de_chaque_terre() {
            float loin = TerrainDeCarte.PORTEE_DES_FRONTIERES_KM; Color32 rouge = Color.red, bleu = Color.blue, vert = Color.green;
            objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>();
            Assert.IsTrue(carte.DistanceALaFrontiere(0, 0) == -1f && !carte.Rattacher(7, "a", Color.red) && carte.PaysDe(7) == null, "une carte avant la pose a des pays ou des frontières");
            var deux = new CarteLue(2, new[] { Carre(7, 0), Carre(8, 10000) }); carte.Montrer(deux, FormesDeTest.UnLieuParCellule(deux));
            Assert.IsTrue(carte.PaysDe(7) == null && carte.PaysDe(8) == null && carte.DistanceALaFrontiere(-.5f, .5f) == loin, "deux terres sans puissance ont une frontière : " + carte.DistanceALaFrontiere(-.5f, .5f));
            Assert.IsTrue(carte.Rattacher(7, "a", Color.red) && carte.Rattacher(8, "b", Color.blue) && carte.PaysDe(7) == "a" && carte.PaysDe(8) == "b", "les terres ne sont pas rattachées");
            // La distance à la frontière est celle du côté commun, des deux côtés ; la côte n'est pas une frontière.
            foreach (float x in new[] { -3.5f, -.5f, .5f, 3.5f }) Assert.AreEqual(Mathf.Abs(x), carte.DistanceALaFrontiere(x, .5f), .1f, "en x = " + x);
            Assert.AreEqual(9.5f, carte.DistanceALaFrontiere(-9.5f, .5f), .1f, "au rivage, la frontière n'est pas celle du côté commun");
            Assert.AreEqual(loin, carte.DistanceALaFrontiere(.5f, 5.5f), "une frontière est mesurée en mer");
            // Les tables versées au shader : l'indice du pays à la case de la cellule, la couleur du liseré à la case du pays.
            Verser(); int a = PaysVerse(0), b = PaysVerse(1);
            Assert.IsTrue(a > 0 && b > 0 && a != b, "indices versés : " + a + ", " + b);
            Assert.IsTrue(Proches(LisereVerse(a), rouge) && Proches(LisereVerse(b), bleu) && LisereVerse(0).a == 0, "liserés versés : " + LisereVerse(a) + ", " + LisereVerse(b) + ", sans pays " + LisereVerse(0));
            // Contre-épreuve : un seul pays, aucune frontière ; elle revient avec le second pays.
            Assert.IsTrue(carte.Rattacher(8, "a", Color.red)); Assert.AreEqual(loin, carte.DistanceALaFrontiere(-.5f, .5f), "une frontière au milieu d'un pays");
            Verser(); Assert.AreEqual(PaysVerse(0), PaysVerse(1), "deux terres du même pays n'ont pas le même indice versé");
            Assert.IsTrue(carte.Rattacher(8, "b", Color.blue)); Assert.AreEqual(.5f, carte.DistanceALaFrontiere(-.5f, .5f), .1f, "la frontière n'est pas revenue");
            // Une terre sans pays a une frontière avec celle d'un pays, aucune avec une autre terre sans pays.
            Assert.IsTrue(carte.Rattacher(8, null, Color.clear) && carte.PaysDe(8) == null); Assert.AreEqual(.5f, carte.DistanceALaFrontiere(.5f, .5f), .1f, "pas de frontière entre un pays et une terre sans pays");
            Verser(); Assert.AreEqual(0, PaysVerse(1), "une terre sans pays a un indice de pays");
            Assert.IsTrue(carte.Rattacher(7, "", Color.clear) && carte.PaysDe(7) == null); Assert.AreEqual(loin, carte.DistanceALaFrontiere(.5f, .5f), "une frontière entre deux terres sans pays");
            Assert.IsFalse(carte.Rattacher(-5, "a", Color.red), "une cellule non servie a été rattachée");
            // Plus de pays que la table n'a de cases : elle se resserre sur ceux qui tiennent une terre, sans en mêler deux.
            Assert.IsTrue(carte.Rattacher(7, "a", Color.red)); int cases = Matiere.GetTexture("_Pays").width * Matiere.GetTexture("_Pays").height, pays = cases + 44;
            for (int k = 0; k < pays; k++) Assert.IsTrue(carte.Rattacher(8, "p" + k, Color.green), "p" + k);
            Assert.IsTrue(carte.PaysDe(7) == "a" && carte.PaysDe(8) == "p" + (pays - 1), carte.PaysDe(7) + ", " + carte.PaysDe(8));
            Assert.AreEqual(.5f, carte.DistanceALaFrontiere(-.5f, .5f), .1f, "la table resserrée a perdu la frontière");
            Verser(); a = PaysVerse(0); b = PaysVerse(1);
            Assert.IsTrue(a > 0 && b > 0 && a != b && a < cases && b < cases && Proches(LisereVerse(a), rouge) && Proches(LisereVerse(b), vert), "après " + pays + " pays : indices " + a + " et " + b + ", liserés " + LisereVerse(a) + " et " + LisereVerse(b));
            // Une cellule retirée n'a plus de pays et ne fait plus de frontière.
            Assert.IsTrue(carte.Retirer(8) && carte.PaysDe(8) == null && !carte.Rattacher(8, "b", Color.blue), "une cellule retirée garde un pays");
            Assert.AreEqual(loin, carte.DistanceALaFrontiere(-.5f, .5f), "une frontière avec une cellule retirée");
        }
        // Un shader ne se compile qu'à son premier dessin : une erreur y laisse la carte sans un trait, ou sans un nom, et
        // tous les autres tests verts. Les passes de chaque shader de la carte sont donc compilées ici, et aucune ne rend d'erreur.
        [Test] public void Le_shader_du_terrain_se_compile_sans_erreur() => Compiler(CarteDessinee.SHADER_DU_TERRAIN, 2);
        [Test] public void Le_shader_des_noms_se_compile_sans_erreur() => Compiler("Forge/NomDeCarte", 1);
        [Test] public void Le_shader_des_figurines_se_compile_sans_erreur() => Compiler(FormesDeCarte.SHADER, 2);
        // Le terrain se dessine d'abord ; les noms des pays s'impriment sur lui, sans épreuve de profondeur ; puis viennent
        // les objets posés sur la carte, qui passent devant eux. C'est l'ordre des files des deux shaders qui le dit.
        [Test] public void Les_noms_s_impriment_apres_le_terrain_et_avant_les_objets() {
            Shader terrain = Resources.Load<Shader>(CarteDessinee.SHADER_DU_TERRAIN), noms = Resources.Load<Shader>("Forge/NomDeCarte"); int objets = (int)UnityEngine.Rendering.RenderQueue.Geometry;
            Assert.IsTrue(terrain.renderQueue < noms.renderQueue && noms.renderQueue < objets, "terrain " + terrain.renderQueue + ", noms " + noms.renderQueue + ", objets " + objets);
            Assert.Less(noms.renderQueue - 1, objets, "le halo des noms, une file avant leur encre"); Assert.Greater(noms.renderQueue - 1, terrain.renderQueue, "le halo des noms passe avant le terrain");
        }
        private static void Compiler(string nom, int passes) {
            Shader shader = Resources.Load<Shader>(nom);
            Assert.IsNotNull(shader, nom);
            var mat = new Material(shader);
            try {
                Assert.AreEqual(passes, mat.passCount, "les passes de " + nom);
                for (int passe = 0; passe < mat.passCount; passe++) UnityEditor.ShaderUtil.CompilePass(mat, passe, true);
                var erreurs = new List<string>();
                foreach (var m in UnityEditor.ShaderUtil.GetShaderMessages(shader))
                    if (m.severity == UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error) erreurs.Add(m.message + " (ligne " + m.line + ")");
                Assert.IsTrue(erreurs.Count == 0 && !UnityEditor.ShaderUtil.ShaderHasError(shader), nom + " : " + erreurs.Count + " erreurs : " + string.Join(" ; ", erreurs));
            } finally { UnityEngine.Object.DestroyImmediate(mat); }
        }
        [Test] public void Le_materiau_de_carte_existe_sans_les_ressources_de_l_editeur() {
            Servir(0, 200, Fixture);
            Attendue(out int servies);
            var global = UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline;
            var qualite = QualitySettings.renderPipeline;
            try {
                UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline = null;
                QualitySettings.renderPipeline = null;
                Poser();
                Lire(1);
                Assert.Greater(servies, 0);
                Assert.AreEqual(servies, carte.CellulesPosees, carte.TexteAffiche);
                Assert.AreEqual(servies, carte.CellulesServies);
                foreach (var rendu in objet.GetComponentsInChildren<MeshRenderer>())
                    Assert.IsNotNull(rendu.sharedMaterial.shader, rendu.name);
            } finally {
                UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline = global;
                QualitySettings.renderPipeline = qualite;
            }
        }
        [Test] public void Sans_service_aucune_cellule_et_le_message() {
            Poser(); Lire(1);
            Absence("service absent sur 127.0.0.1:" + port);
            Servir(0, 200, Fixture); Attendue(out int servies);
            carte.Pas(2); Assert.IsTrue(!carte.LectureEnVol && Volatile.Read(ref requetes) == 0, "une lecture est partie 1 s après l'absence");
            Lire(3.5);
            Assert.IsTrue(Volatile.Read(ref requetes) == 2 && servies == 596 && carte.CellulesPosees == servies && carte.CellulesServies == servies, carte.TexteAffiche);
            Assert.IsTrue(carte.TexteAffiche == "" && objet.GetComponentInChildren<Text>() == null);
        }
        [TestCase(404, "statut 404")] [TestCase(200, "JSON invalide")]
        public void Une_reponse_illisible_ne_pose_rien(int statut, string cause) {
            byte[] fixture = Fixture, moitie = new byte[fixture.Length / 2]; Array.Copy(fixture, moitie, moitie.Length);
            Servir(0, statut, statut == 200 ? moitie : System.Text.Encoding.UTF8.GetBytes("{\"erreur\":\"introuvable\"}"));
            Poser(); Lire(1); Absence(cause);
        }
        [Test] public void Le_pas_ne_bloque_pas_pendant_la_lecture() {
            Servir(LENTEUR_MS, 200, Fixture); Poser();
            var montre = Stopwatch.StartNew(); carte.Pas(1); montre.Stop();
            Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le pas a attendu le service");
            Assert.IsTrue(carte.LectureEnVol);
        }
        // Noms et caméra, avec ou sans caméra donnée. L'attendu : la carte lue par ClientCarte, l'origine de Mailler, et la conversion écrite ici.
        private CarteLue Lue(out PointCarte origine) {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence); Interlocked.Exchange(ref requetes, 0); origine = MaillageDeCarte.Mailler(lecture.Carte).Origine; return lecture.Carte;
        }
        private static Vector3 Converti(PointCarte p, PointCarte o, float y) => new Vector3((float)((p.X - o.X) / 1000), y, (float)((p.Y - o.Y) / 1000));
        // Le même point posé à cette hauteur au-dessus du sol dessiné (en mer, au-dessus de l'eau) : là où la carte pose ses noms.
        private Vector3 SurLeSol(PointCarte p, PointCarte o, float hauteur) { Vector3 v = Converti(p, o, 0f); v.y = Mathf.Max(carte.HauteurDuSol(v.x, v.z), 0f) + hauteur; return v; }
        private static bool Egal(Vector3 a, Vector3 b) => a.x == b.x && a.y == b.y && a.z == b.z; // `==` de Vector3 tolère un écart : on compare composante par composante
        private int Nommes(string nom) { int n = 0; foreach (Transform t in objet.GetComponentsInChildren<Transform>(true)) if (t.name == nom) n++; return n; }
        // Les traits de la carte (bords des cellules, côte, frontières) se dessinent dans le terrain, d'après ses
        // distances : aucun contour n'est posé au-dessus de lui, et chaque point servi d'un anneau est près d'un trait.
        // Le service simplifie chaque anneau à part : deux bords voisins ne coïncident pas partout, et le terrain n'en
        // trace qu'un, celui de la cellule servie la première. Un point de l'autre bord en est donc à la largeur de la
        // fente ou du recouvrement, d'où la part tolérée au-delà de deux texels. Les autres points sans trait sont au
        // bout d'une aiguille de terre ou de mer plus fine qu'un texel, dont la grille n'a rien gardé : autour d'eux,
        // elle dit partout la même cellule.
        [Test] public void Les_traits_viennent_du_terrain_sans_aucun_contour_pose() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1);
            Assert.IsTrue(objet.GetComponentsInChildren<LineRenderer>(true).Length == 0 && Nommes("Contours de la carte") == 0, objet.GetComponentsInChildren<LineRenderer>(true).Length + " trait(s) posé(s) au-dessus du terrain");
            TerrainDeCarte t = carte.Terrain;
            Assert.IsTrue(t.Bords.Count == 2 * t.Largeur * t.Hauteur && t.Separations > 0, t.Bords.Count + " distances, " + t.Separations + " séparations");
            int points = 0, anneaux = 0, eloignes = 0, dessinables = 0; float pire = 0f, seuil = 2f * t.Pas;
            foreach (CelluleDeCarte c in lue.Cellules)
                foreach (PolygoneDeCarte p in c.Contour) {
                    var tous = new List<IReadOnlyList<PointCarte>> { p.Exterieur }; tous.AddRange(p.Trous);
                    foreach (IReadOnlyList<PointCarte> a in tous) { anneaux++;
                        foreach (PointCarte q in a) {
                            Vector3 v = Converti(q, o, 0f); float d = Mathf.Min(t.BordEn(v.x, v.z), t.CoteEn(v.x, v.z));
                            points++; if (d > pire) pire = d;
                            if (d <= seuil) continue;
                            eloignes++; int ici = t.CelluleEn(v.x, v.z); bool unie = true;
                            for (int dj = -1; dj <= 1; dj++)
                                for (int di = -1; di <= 1; di++)
                                    if (t.CelluleEn(v.x + di * t.Pas, v.z + dj * t.Pas) != ici) unie = false;
                            if (!unie) dessinables++;
                        }
                    }
                }
            TestContext.Out.WriteLine(points + " points servis sur " + anneaux + " anneaux, " + eloignes + " à plus de " + seuil + " km d'un trait, le pire à " + pire + " km, " + t.Separations + " séparations");
            Assert.IsTrue(anneaux == 746 && points == 19789, anneaux + " anneaux, " + points + " points");
            Assert.LessOrEqual(eloignes, points / 100, eloignes + " points servis sur " + points + " sont à plus de " + seuil + " km d'un trait du terrain");
            Assert.AreEqual(0, dessinables, dessinables + " points servis sans trait ont, à un texel d'eux, deux cellules que la grille distingue");
            // Contre-épreuve : au cœur des terres, des texels sont hors de portée de tout bord.
            int auCoeur = 0;
            for (int j = 8; j < t.Hauteur; j += 16)
                for (int i = 8; i < t.Largeur; i += 16) {
                    float x = t.Coin.x + (i + .5f) * t.Pas, z = t.Coin.y + (j + .5f) * t.Pas;
                    if (t.CelluleEn(x, z) != 0 && t.BordEn(x, z) == TerrainDeCarte.PORTEE_DES_BORDS_KM) auCoeur++;
                }
            Assert.Greater(auCoeur, 100, "aucune terre n'est loin d'un bord : la distance ne juge rien");
            Assert.IsTrue(carte.CellulesPosees == 596 && TerrainsSousLaCarte == 1, TerrainsSousLaCarte + " MeshFilter sous la carte");
        }
        private void Noms(CarteLue lue, PointCarte o) {
            TextMesh[] noms = objet.transform.Find("Villes de la carte").GetComponentsInChildren<TextMesh>(true);
            var vus = new HashSet<string>(); int i = 0;
            foreach (CelluleDeCarte c in lue.Cellules)
                foreach (VilleDeCarte v in c.Villes) {
                    Assert.Less(i, noms.Length, "moins de noms que de villes"); TextMesh n = noms[i++]; vus.Add(v.Nom);
                    Assert.IsTrue(n.text == v.Nom && n.name == "Ville " + v.Nom, n.name + " pour " + v.Nom);
                    Vector3 attendu = SurLeSol(v.Position, o, CarteDessinee.HAUTEUR_NOM); Assert.IsTrue(Egal(n.transform.localPosition, attendu),v.Nom + " en " + n.transform.localPosition.ToString("R") + ", attendu " + attendu.ToString("R"));
                    Assert.IsTrue(n.transform.localRotation == Quaternion.Euler(90, 0, 0), v.Nom + " tourné de " + n.transform.localEulerAngles);
                }
            Assert.IsTrue(i == noms.Length && i == 57 && vus.Count == i && vus.Contains("Constantinople"), i + " villes, " + noms.Length + " noms, " + vus.Count + " distincts");
        }
        [Test] public void Chaque_ville_servie_a_son_nom() { Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1); Noms(lue, o);
            Assert.IsNull(objet.GetComponentInChildren<Text>(), "un Text d'UI actif sous la carte");
        }
        // La conversion exposée est celle des noms : rien avant la pose, la place de chaque nom posé ensuite.
        [Test] public void La_position_sur_la_carte_est_celle_des_noms() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Assert.IsNull(carte.PositionSurLaCarte(o, CarteDessinee.HAUTEUR_NOM), "une position avant la pose");
            Lire(1); Transform noms = objet.transform.Find("Villes de la carte"); int i = 0;
            foreach (CelluleDeCarte c in lue.Cellules) foreach (VilleDeCarte v in c.Villes) { Vector3? p = carte.PositionSurLaCarte(v.Position, CarteDessinee.HAUTEUR_NOM);
                Assert.IsTrue(p.HasValue && Egal(p.Value, noms.GetChild(i++).localPosition) && Egal(p.Value, SurLeSol(v.Position, o, CarteDessinee.HAUTEUR_NOM)), v.Nom + " en " + p); }
            Assert.IsTrue(i == 57 && i == noms.childCount, i + " villes, " + noms.childCount + " noms");
        }
        // Au plus loin, la caméra de la carte montre toute la carte : quelle que soit la forme de la fenêtre, les quatre
        // coins de ses bornes tombent dans l'écran, et la carte touche le bord de l'écran sur son axe le plus serré.
        [Test] public void Au_plus_loin_la_camera_montre_toute_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; Canvas toile = objet.GetComponentInChildren<Canvas>(true);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && cam != null && cam.name == "Caméra de la carte" && cam.transform.parent == objet.transform && !cam.orthographic, "caméra de la carte absente, ou pas en perspective");
            Assert.IsTrue(toile.renderMode == RenderMode.ScreenSpaceCamera && toile.worldCamera == cam, "la toile n'est pas sur la caméra de la carte");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            Rect cadre = carte.Cadre; Assert.IsTrue(cadre.xMin < minX && cadre.yMin < minZ && cadre.xMax > maxX && cadre.yMax > maxZ, "les bornes ne contiennent pas les cellules : " + cadre);
            Vector2 Sol(Vector2 ancre) {
                Ray r = cam.ViewportPointToRay(new Vector3(ancre.x, ancre.y, 0)); Vector3 p = objet.transform.InverseTransformPoint(r.origin), d = objet.transform.InverseTransformDirection(r.direction);
                float t = -p.y / d.y; return new Vector2(p.x + d.x * t, p.z + d.z * t);
            }
            foreach (float aspect in new[] { 16f / 9f, 4f / 3f, 0.5f, 2.4f }) {
                cam.aspect = aspect; carte.Vue.Zoomer(-1000, new Vector2(.5f, .5f)); carte.Pas(2); float touche = 0f;
                foreach (var coin in new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up }) {
                    Vector3 f = cam.WorldToViewportPoint(objet.transform.TransformPoint(new Vector3(Mathf.Lerp(cadre.xMin, cadre.xMax, coin.x), 0f, Mathf.Lerp(cadre.yMin, cadre.yMax, coin.y))));
                    Assert.IsTrue(f.x >= -1e-4f && f.x <= 1f + 1e-4f && f.y >= -1e-4f && f.y <= 1f + 1e-4f, "aspect " + aspect + ", le coin " + coin + " de la carte sort de l'écran : " + f);
                    touche = Mathf.Max(touche, Mathf.Abs(f.x - .5f) * 2f, Mathf.Abs(f.y - .5f) * 2f);
                }
                Assert.AreEqual(1f, touche, 1e-3f, "aspect " + aspect + " : au plus loin, la carte ne touche pas le bord de l'écran");
                Assert.Greater(Sol(Vector2.up).y, Sol(Vector2.zero).y, "aspect " + aspect + " : le nord n'est pas en haut");
            }
        }
        [Test] public void Sans_carte_ni_contour_ni_nom() {
            Poser(); Lire(1);
            Assert.IsTrue(objet.GetComponentsInChildren<LineRenderer>(true).Length == 0 && objet.GetComponentsInChildren<TextMesh>(true).Length == 0, carte.TexteAffiche);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && carte.camera != null && carte.camera.name == "Caméra de la carte", "pas de caméra de la carte sans carte");
        }
        [Test] public void Une_camera_donnee_n_est_pas_cadree() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); int servies = lue.Cellules.Count;
            Camera donnee = new GameObject("Caméra donnée du test").AddComponent<Camera>(); Vector3 position = new Vector3(5, 6, 7); Quaternion rotation = Quaternion.Euler(10, 20, 30);
            try {
                donnee.orthographic = false; donnee.transform.SetPositionAndRotation(position, rotation);
                objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.camera = donnee; carte.Demarrer();
                Lire(1); for (int i = 1; i <= 5; i++) carte.Pas(1 + i);
                Assert.IsTrue(carte.CellulesPosees == servies && carte.camera == donnee && Nommes("Caméra de la carte") == 0, carte.CellulesPosees + " cellules, " + Nommes("Caméra de la carte") + " caméra(s) créée(s)");
                Assert.IsTrue(Egal(donnee.transform.position, position) && donnee.transform.rotation == rotation && !donnee.orthographic, "la caméra donnée a été touchée : " + donnee.transform.position + " " + donnee.transform.eulerAngles);
                Noms(lue, o); // avec une caméra donnée aussi, la carte nomme ses villes
            } finally { UnityEngine.Object.DestroyImmediate(donnee.gameObject); }
        }
        // La caméra créée montre la vue que le joueur glisse et zoome : en perspective, à la verticale, nord en haut, à
        // toute échelle, sans sortir de la carte servie. Le cas juge sa pose par les rayons de l'écran, qui doivent
        // tomber au sol là où la vue le dit.
        [Test] public void La_camera_de_la_carte_suit_la_vue_sans_sortir_de_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; cam.aspect = 16f / 9f; carte.Pas(2);
            Assert.IsNotNull(carte.Vue, "pas de vue sur une carte posée"); Assert.IsTrue(carte.Vue.Echelle < 1f && (carte.Vue.Centre - carte.Cadre.center).magnitude < 1e-2f,"la carte ne s'ouvre pas centrée, en deçà du plus loin");
            Assert.IsTrue(!cam.orthographic && Mathf.Abs(cam.fieldOfView - VueDeCarte.CHAMP) < 1e-3f, "la caméra de la carte n'est pas en perspective, au champ de la vue");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            // La vue ne sort pas de la planche : les cellules et le cadre autour d'elles.
            (minX, minZ, maxX, maxZ) = (carte.Cadre.xMin, carte.Cadre.yMin, carte.Cadre.xMax, carte.Cadre.yMax);
            // Le point du niveau de la mer que touche le rayon de la caméra par une ancre de l'écran, en local.
            Vector2 Sol(Vector2 ancre) {
                Ray r = cam.ViewportPointToRay(new Vector3(ancre.x, ancre.y, 0)); Vector3 p = objet.transform.InverseTransformPoint(r.origin), d = objet.transform.InverseTransformDirection(r.direction);
                float t = -p.y / d.y; return new Vector2(p.x + d.x * t, p.z + d.z * t);
            }
            // La vue du départ remplit l'écran de la carte : les quatre coins de l'écran tombent dans ses bornes.
            foreach (var coin in new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up }) {
                Vector2 sol = Sol(coin);
                Assert.IsTrue(sol.x >= minX - 1e-1f && sol.x <= maxX + 1e-1f && sol.y >= minZ - 1e-1f && sol.y <= maxZ + 1e-1f, "le coin " + coin + " de l'écran tombe hors de la carte : " + sol);
            }
            float loin = carte.Vue.Distance; Assert.Less(Vector3.Angle(cam.transform.forward, Vector3.down), 1e-2f, "sur toute la carte, la caméra ne regarde pas à la verticale");
            foreach (var (crans, glisse) in new[] { (12f, new Vector2(0, 0)), (0f, new Vector2(1e7f, 1e7f)), (0f, new Vector2(-1e7f, -1e7f)), (-1000f, new Vector2(0, 0)) }) {
                carte.Vue.Zoomer(crans, new Vector2(.3f, .6f)); carte.Vue.Glisser(glisse, 900f); carte.Pas(3);
                string quand = "crans " + crans + ", glissé " + glisse; float tolerance = 3e-4f * carte.Vue.Demi;
                Assert.Less((cam.transform.position - objet.transform.TransformPoint(carte.Vue.Position)).magnitude, 5e-2f, quand + " : la caméra n'est pas là où la vue la met");
                Assert.Less(Vector3.Angle(cam.transform.forward, objet.transform.TransformDirection(carte.Vue.Regard)), 1e-2f, quand + " : la caméra ne regarde pas où la vue regarde");
                Assert.Less(Vector3.Angle(cam.transform.forward, Vector3.down), 1e-2f, quand + " : la caméra ne regarde pas à la verticale");
                Assert.Less(Vector3.Angle(cam.transform.up, objet.transform.TransformDirection(Vector3.forward)), 1e-2f, quand + " : le haut de l'écran n'est pas le nord de la carte");
                Assert.Less((Sol(new Vector2(.5f, .5f)) - carte.Vue.Centre).magnitude, tolerance, quand + " : la caméra ne vise pas le centre de la vue");
                foreach (Vector2 ancre in new[] { new Vector2(.3f, .6f), new Vector2(.9f, .1f), new Vector2(.05f, .95f) })
                    Assert.Less((Sol(ancre) - carte.Vue.PointSous(ancre)).magnitude, tolerance, quand + " : le rayon de l'écran en " + ancre + " ne tombe pas où la vue le dit");
                // Le point visé, au sol sous le milieu de la partie libre, reste dans la boîte de la carte ; glissé au loin, il en touche le coin.
                Vector2 vise = Sol(carte.Vue.Libre.center);
                Assert.IsTrue(vise.x >= minX - tolerance && vise.x <= maxX + tolerance && vise.y >= minZ - tolerance && vise.y <= maxZ + tolerance, quand + " : le point visé sort de la carte : " + vise);
                if (crans < 0) { Assert.AreEqual(1f, carte.Vue.Echelle, quand + " : la vue n'est pas au plus loin"); Assert.Greater(carte.Vue.Distance, loin, "au plus loin, la vue ne recule pas au-delà de l'ouverture"); continue; }
                if (glisse.x != 0f) Assert.Less((vise - (glisse.x > 0 ? new Vector2(minX, minZ) : new Vector2(maxX, maxZ))).magnitude, tolerance, quand + " : le point visé ne va pas jusqu'au coin de la carte : " + vise);
                else Assert.Less(carte.Vue.Distance, loin / 4, quand + " : la vue ne s'est pas approchée");
            }
        }
        // Le terrain se dessine en relief, la mer au niveau 0 : ce que la carte pose se pose sur ce sol, et le rayon de
        // l'écran trouve le point du relief qu'il touche le premier, pas celui d'un plan. Sur les Alpes, vues de près
        // d'en haut, en 1600 × 900.
        [Test] public void Le_rayon_de_l_ecran_trouve_le_relief_et_le_geste_y_tient_son_point() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1);
            var ecran = new RenderTexture(1600, 900, 16); Camera cam = carte.camera; cam.targetTexture = ecran;
            try {
                // Le maillage levé, sa plus haute cime au plan 0, est posé la mer au niveau 0 et ses hauteurs réduites.
                Transform sol = objet.transform.Find(CarteDessinee.TERRAIN); TerrainDeCarte t = carte.Terrain;
                Assert.IsTrue(sol.localScale == new Vector3(1f, CarteDessinee.ECHELLE_DU_RELIEF, 1f) && Mathf.Abs(sol.localPosition.y - TerrainDeCarte.PLAFOND * CarteDessinee.ECHELLE_DU_RELIEF) < 1e-5f, "le terrain n'est pas posé la mer au niveau 0 : " + sol.localPosition + " × " + sol.localScale);
                VilleDeCarte milan = null; foreach (CelluleDeCarte c in lue.Cellules) foreach (VilleDeCarte v in c.Villes) if (v.Nom == "Milan") milan = v;
                Assert.IsNotNull(milan, "la carte figée ne sert pas Milan"); Vector3 ici = carte.PositionSurLaCarte(milan.Position, 0f).Value;
                Assert.AreEqual(Mathf.Max(carte.HauteurDuSol(ici.x, ici.z), 0f), ici.y, 1e-5f, "un point posé à la hauteur 0 n'est pas sur le sol");
                Assert.AreEqual((t.SolDuMaillage(ici.x, ici.z) + TerrainDeCarte.PLAFOND) * CarteDessinee.ECHELLE_DU_RELIEF, carte.HauteurDuSol(ici.x, ici.z), 1e-5f);
                carte.Vue.Changer(16f / 9f); carte.Vue.Centrer(new Vector2(ici.x, ici.z) + new Vector2(0f, 120f), 160f); carte.Pas(2);
                Vector3 camLocale = objet.transform.InverseTransformPoint(cam.transform.position);
                int points = 0, autreCellule = 0; float pireEcart = 0f, plusHaut = 0f; Vector2 pixelDuPlusHaut = default;
                for (int j = 1; j < 9; j++)
                    for (int i = 1; i < 16; i++) {
                        var pixel = new Vector2(i * 100, j * 100); Vector3? touche = carte.SolSous(pixel);
                        Assert.IsTrue(touche.HasValue, "aucun sol sous le pixel " + pixel); Vector3 local = objet.transform.InverseTransformPoint(touche.Value);
                        Assert.Less(Mathf.Abs(local.y - carte.HauteurDuSol(local.x, local.z)), 0.02f, "le point rendu sous " + pixel + " n'est pas sur le sol");
                        Assert.Less(((Vector2)cam.WorldToScreenPoint(touche.Value) - pixel).magnitude, 0.5f, "le point rendu n'est pas sous le pixel " + pixel);
                        // Premier contact : de la caméra à lui, le rayon reste au-dessus du sol.
                        for (int k = 1; k < 400; k++) { Vector3 p = Vector3.Lerp(camLocale, local, k / 400f); Assert.Greater(p.y, carte.HauteurDuSol(p.x, p.z) - 0.25f, "le rayon du pixel " + pixel + " traverse le relief avant son point"); }
                        Assert.AreSame(carte.CelluleSous(touche.Value), carte.CelluleSous(objet.transform.TransformPoint(new Vector3(local.x, 0f, local.z))), "la cellule ne se lit pas à la verticale du point");
                        // Le même pixel lu sur un plan, au niveau de la mer : plus loin que le relief, parfois dans une autre cellule.
                        Vector2 plat = carte.Vue.PointSous(cam.ScreenToViewportPoint(pixel)); float ecart = (plat - new Vector2(local.x, local.z)).magnitude;
                        if (ecart > pireEcart) pireEcart = ecart; if (t.CelluleEn(plat.x, plat.y) != t.CelluleEn(local.x, local.z)) autreCellule++;
                        if (local.y > plusHaut) { plusHaut = local.y; pixelDuPlusHaut = pixel; }
                        points++;
                    }
                UnityEngine.Debug.Log("SOL SOUS L'ECRAN : " + points + " pixels sur les Alpes ; plus haut point touché " + plusHaut.ToString("0.00") + " km ; écart au plan jusqu'à " + pireEcart.ToString("0.00") + " km ; " + autreCellule + " pixels dans une autre cellule sur un plan");
                Assert.Greater(plusHaut, 3f, "échantillon vide : aucune montagne sous l'écran"); Assert.Greater(pireEcart, 2f, "échantillon vide : le relief ne déplace aucun point");
                Assert.IsNull(carte.SolSur(new Ray(cam.transform.position, Vector3.up)), "un rayon qui monte trouve un sol");

                // Le geste : le point de la montagne saisi reste sous la souris pendant le glissé, puis pendant la molette.
                var geste = new ParcoursDeVue(); Vector2 appui = pixelDuPlusHaut, plusLoin = appui + new Vector2(appui.x < 800 ? 320 : -320, appui.y < 450 ? 210 : -210);
                Vector3 saisi = carte.SolSous(appui).Value; Vector2 centre = carte.Vue.Centre;
                geste.Pas(carte, appui, true, true, 0f); carte.Pas(3); Assert.IsTrue(geste.Glisse && carte.Vue.Centre == centre, "l'appui a bougé la carte");
                Assert.Less((objet.transform.TransformPoint(geste.Saisi.Value) - saisi).magnitude, 1e-2f, "le point saisi n'est pas celui du sol sous la souris");
                geste.Pas(carte, plusLoin, false, true, 0f); carte.Pas(4);
                Assert.Greater((carte.Vue.Centre - centre).magnitude, 20f, "la carte n'a pas suivi la souris");
                Assert.Less((carte.SolSous(plusLoin).Value - saisi).magnitude, 0.3f, "glissé : le point saisi n'est plus sous la souris");
                // Contre-épreuve : le même glissé mesuré sur un plan aurait laissé la montagne ailleurs.
                Assert.Greater((carte.Vue.PointSous(cam.ScreenToViewportPoint(plusLoin)) - new Vector2(objet.transform.InverseTransformPoint(saisi).x, objet.transform.InverseTransformPoint(saisi).z)).magnitude, 1f, "échantillon vide : le point saisi est au niveau de la mer");
                geste.Pas(carte, plusLoin, false, false, 0f); Assert.IsFalse(geste.Glisse, "le bouton relâché tient encore la carte");
                float demi = carte.Vue.Demi; geste.Pas(carte, plusLoin, false, false, 3f); carte.Pas(5);
                Assert.Less(carte.Vue.Demi, demi, "la molette n'a pas rapproché la vue"); Assert.Less((carte.SolSous(plusLoin).Value - saisi).magnitude, 0.5f, "molette : le point sous la souris a bougé");
                // Sans bouton tenu, la souris qui bouge ne déplace rien.
                centre = carte.Vue.Centre; geste.Pas(carte, appui, false, false, 0f); Assert.AreEqual(centre, carte.Vue.Centre, "la carte suit une souris qui ne la tient pas");

                // Une ligne drapée suit le sol, un point tous les six km au plus.
                Vector3 de = carte.SurLeSol(ici.x, ici.z, 0.5f), vers = carte.SurLeSol(ici.x + 40f, ici.z + 110f, 0.5f); List<Vector3> ligne = carte.Draper(de, vers, 0.5f);
                Assert.IsTrue(ligne.Count >= 21 && (ligne[0] - de).magnitude < 1e-3f && (ligne[ligne.Count - 1] - vers).magnitude < 1e-3f, ligne.Count + " points, de " + ligne[0] + " à " + ligne[ligne.Count - 1]);
                float denivele = 0f;
                for (int k = 0; k < ligne.Count; k++) {
                    Assert.AreEqual(Mathf.Max(carte.HauteurDuSol(ligne[k].x, ligne[k].z), 0f) + 0.5f, ligne[k].y, 1e-4f, "le point " + k + " de la ligne n'est pas à sa hauteur au-dessus du sol");
                    if (k > 0) { Assert.LessOrEqual(new Vector2(ligne[k].x - ligne[k - 1].x, ligne[k].z - ligne[k - 1].z).magnitude, CarteDessinee.PAS_DU_DRAPE_KM + 1e-3f); denivele = Mathf.Max(denivele, Mathf.Abs(ligne[k].y - ligne[0].y)); }
                }
                Assert.Greater(denivele, 1f, "échantillon vide : la ligne ne monte ni ne descend");
            } finally { cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(ecran); }
        }
        // Les réponses figées de l'Ouest, chacune à son chemin.
        private void ServirOuest() {
            string dossier = Application.dataPath + "/ForgeLocal3D/Pont/Tests/";
            formes = File.ReadAllBytes(dossier + FormesDeTest.FORMES); Servir(0, 200, File.ReadAllBytes(dossier + FormesDeTest.CARTE));
        }
        private int RangServi(long cellId) { for (int r = 0; r < carte.Lue.Cellules.Count; r++) if (carte.Lue.Cellules[r].CellId == cellId) return r; throw new ArgumentException("cellule " + cellId + " non servie"); }
        // Sans formes, ou avec des formes que le levé refuse, la carte ne se pose pas : elle dit pourquoi elle ne se
        // dessine pas, ne dessine aucune cellule seule, et la lecture repart.
        [Test] public void Sans_formes_la_carte_ne_se_dessine_pas_et_dit_pourquoi() {
            statutDesFormes = 404; formes = System.Text.Encoding.UTF8.GetBytes("{\"erreur\":\"introuvable\"}"); Servir(0, 200, Fixture); Poser(); Lire(1);
            Assert.IsTrue(carte.CellulesPosees == 0 && carte.CellulesServies == -1 && carte.Terrain == null && TerrainsSousLaCarte == 0, carte.CellulesPosees + " posées, " + TerrainsSousLaCarte + " terrain(s)");
            StringAssert.StartsWith(CarteDessinee.NON_DESSINEE + "formes : statut 404", carte.TexteAffiche); Assert.IsTrue(objet.GetComponentInChildren<Text>().text == carte.TexteAffiche);
            Assert.AreEqual(2, Volatile.Read(ref requetes), "la carte ne demande pas ses formes après la carte");
            // Des formes qui ne sont pas celles de la carte : le levé les refuse, et la carte le dit à la lecture suivante.
            formes = File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + FormesDeTest.FORMES); statutDesFormes = 200; Lire(3.5);
            Assert.IsTrue(carte.CellulesPosees == 0 && carte.Terrain == null, carte.TexteAffiche);
            StringAssert.StartsWith(CarteDessinee.NON_DESSINEE + "formes : des formes de 16 cellules pour une carte de 596", carte.TexteAffiche);
            // Les formes de la carte servies, la lecture qui repart pose la carte.
            formes = FormesDuFixture; Lire(6);
            Assert.IsTrue(carte.CellulesPosees == 596 && carte.TexteAffiche == "" && Volatile.Read(ref requetes) == 6, carte.TexteAffiche + " ; " + requetes + " requêtes");
        }
        // Chaque lieu de la cellule de Pampelune est d'abord à la Navarre, le pays de sa cellule. Ses lieux castillans
        // (`autres_pays` de `/terres`) rattachés à la Castille, une frontière passe entre eux et les autres, à l'intérieur
        // de la cellule ; leur liseré est celui de leur pays. Rejouer le même rattachement, de la cellule puis de ses
        // lieux, ne remesure rien ; un vrai changement remesure.
        [Test] public void Un_lieu_rattache_a_un_autre_pays_fait_naitre_une_frontiere_dans_sa_cellule() {
            ServirOuest(); Poser(); Lire(1); TerrainDeCarte t = carte.Terrain; int rang = RangServi(FormesDeTest.PAMPELUNE), premier = t.PremierLieuDe(rang);
            TerreLue pampelune = FormesDeTest.TerresOuest.Terres.Single(x => x.CellId == FormesDeTest.PAMPELUNE);
            var castillans = new HashSet<long>(pampelune.AutresPays.Select(a => a.Rang));
            string navarre = carte.PaysDe(FormesDeTest.PAMPELUNE), castille = carte.PaysDe(10196); Color rouge = Color.red, bleu = Color.blue;
            Assert.IsTrue(castillans.Count > 0 && !castillans.Contains(0) && navarre != null && castille != null && navarre != castille, "échantillon vide : " + castillans.Count + " lieux castillans, " + navarre + " / " + castille);
            for (int k = 0; k < t.LieuxDe(rang); k++) Assert.AreEqual(navarre, carte.PaysDuLieu(FormesDeTest.PAMPELUNE, t.RangDuLieu(premier + k)), "lieu " + k + " au départ");
            // Les paires de texels voisins de la cellule entre un lieu castillan et un autre.
            var paires = new List<(Vector2, Vector2)>();
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i + 1 < t.Largeur; i++) {
                    int a = t.Lieux[j * t.Largeur + i] - 1, b = t.Lieux[j * t.Largeur + i + 1] - 1;
                    if (a < 0 || b < 0 || a == b || t.CelluleDuLieu(a) != rang || t.CelluleDuLieu(b) != rang || castillans.Contains(t.RangDuLieu(a)) == castillans.Contains(t.RangDuLieu(b))) continue;
                    paires.Add((t.Coin + new Vector2(i + .5f, j + .5f) * t.Pas, t.Coin + new Vector2(i + 1.5f, j + .5f) * t.Pas));
                }
            float Pire() => paires.Max(q => Mathf.Max(carte.DistanceALaFrontiere(q.Item1.x, q.Item1.y), carte.DistanceALaFrontiere(q.Item2.x, q.Item2.y)));
            Assert.Greater(paires.Count, 20, "échantillon vide : aucun lieu castillan n'en touche un autre");
            Assert.Greater(Pire(), 2f * t.Pas, "une frontière passe déjà entre les lieux castillans et les autres");
            foreach (long r in castillans) Assert.IsTrue(carte.RattacherLieu(FormesDeTest.PAMPELUNE, r, castille, rouge), "lieu " + r);
            Assert.LessOrEqual(Pire(), 2f * t.Pas, "pas de frontière entre les lieux castillans de Pampelune et les autres");
            Assert.IsTrue(carte.PaysDe(FormesDeTest.PAMPELUNE) == navarre && carte.PaysDuLieu(FormesDeTest.PAMPELUNE, castillans.First()) == castille, "le rattachement d'un lieu a changé le pays de la cellule");
            Assert.IsTrue(!carte.RattacherLieu(FormesDeTest.PAMPELUNE, t.LieuxDe(rang), castille, rouge) && !carte.RattacherLieu(-5, 0, castille, rouge) && carte.PaysDuLieu(-5, 0) == null, "un lieu que le service ne sert pas a été rattaché");
            Verser(); int lieuCastillan = t.LieuDe(rang, castillans.First());
            Assert.IsTrue(PaysVerse(lieuCastillan) != PaysVerse(premier) && PaysVerse(lieuCastillan) == PaysVerse(t.PremierLieuDe(RangServi(10196))), "le pays versé d'un lieu castillan n'est pas celui de la Castille");
            Assert.IsTrue(Proches(LisereVerse(PaysVerse(lieuCastillan)), rouge), "le liseré d'un lieu castillan n'est pas celui de son pays");
            // Rejouer : la cellule entière à la Navarre, puis ses lieux castillans à la Castille, comme chaque image.
            int mesures = carte.MesuresDesFrontieres;
            for (int fois = 0; fois < 3; fois++) {
                Assert.IsTrue(carte.Rattacher(FormesDeTest.PAMPELUNE, navarre, bleu)); foreach (long r in castillans) carte.RattacherLieu(FormesDeTest.PAMPELUNE, r, castille, rouge);
                Verser();
            }
            Assert.AreEqual(mesures, carte.MesuresDesFrontieres, "le même rattachement rejoué a remesuré les frontières");
            Assert.IsTrue(carte.RattacherLieu(FormesDeTest.PAMPELUNE, 0, castille, rouge)); Verser();
            Assert.AreEqual(mesures + 1, carte.MesuresDesFrontieres, "un lieu qui change de pays ne remesure pas les frontières");
        }
        // Un lieu se teint seul ; la cellule entière se teint par son numéro, et la marque cerne tous ses lieux sans les teindre.
        [Test] public void Un_lieu_se_teint_seul_et_la_cellule_entiere_par_son_numero() {
            ServirOuest(); Poser(); Lire(1); TerrainDeCarte t = carte.Terrain; int rang = RangServi(FormesDeTest.PAMPELUNE), premier = t.PremierLieuDe(rang), n = t.LieuxDe(rang);
            var avant = Enumerable.Range(0, t.NombreDeLieux).Select(Versee).ToArray(); Color neuve = new Color(0.2f, 0.7f, 0.3f, 1f), autre = new Color(0.6f, 0.2f, 0.7f, 1f), marque = new Color(0.9f, 0.9f, 0.1f, 1f);
            Assert.IsTrue(n > 2 && Enumerable.Range(premier, n).All(l => Proches(avant[l], avant[premier])), "les lieux d'une cellule n'ont pas, au départ, la teinte de sa puissance");
            Color depart = carte.TeinteDe(FormesDeTest.PAMPELUNE).Value;
            Assert.IsTrue(carte.TeinterLieu(FormesDeTest.PAMPELUNE, 3, neuve)); carte.Pas(2);
            int changees = Enumerable.Range(0, t.NombreDeLieux).Count(l => !Proches(Versee(l), avant[l]));
            Assert.IsTrue(changees == 1 && Proches(Versee(t.LieuDe(rang, 3)), neuve), changees + " lieux ont changé de teinte");
            Assert.IsTrue(carte.TeinteDuLieu(FormesDeTest.PAMPELUNE, 3) == neuve && carte.TeinteDe(FormesDeTest.PAMPELUNE) == depart, "la teinte d'un lieu a changé celle de la cellule");
            Assert.IsTrue(!carte.TeinterLieu(FormesDeTest.PAMPELUNE, n, neuve) && !carte.TeinterLieu(-5, 0, neuve) && carte.TeinteDuLieu(FormesDeTest.PAMPELUNE, n) == null, "un lieu que le service ne sert pas a été teint");
            Assert.IsTrue(carte.Teinter(FormesDeTest.PAMPELUNE, autre)); carte.Pas(3);
            Assert.IsTrue(Enumerable.Range(premier, n).All(l => Proches(Versee(l), autre)), "la cellule entière n'a pas pris sa teinte");
            Assert.IsTrue(Enumerable.Range(0, t.NombreDeLieux).Where(l => l < premier || l >= premier + n).All(l => Proches(Versee(l), avant[l])), "une autre cellule a changé de teinte");
            Assert.IsTrue(carte.Marquer(FormesDeTest.PAMPELUNE, marque)); carte.Pas(4);
            Assert.IsTrue(Enumerable.Range(premier, n).All(l => Proches(Versee(l), autre)) && carte.TeinteDe(FormesDeTest.PAMPELUNE) == autre, "la marque a teint les lieux de la cellule");
            Assert.AreEqual(new Vector4(premier + 1, premier + n, 0, 0), Matiere.GetVector("_LieuxMarques"), "la marque ne cerne pas tous les lieux de la cellule");
            // Le trait suit le bord de la cellule, pas ceux de ses lieux : sur un bord entre deux de ses lieux, il est loin.
            int interieurs = 0, auBord = 0; RectInt zone = t.ZoneDe(rang);
            for (int j = zone.yMin; j < zone.yMax; j++) for (int i = zone.xMin; i < zone.xMax; i++) {
                int k = j * t.Largeur + i, l = t.Lieux[k] - 1; if (l < premier || l >= premier + n) continue;
                float x = t.Coin.x + (i + .5f) * t.Pas, z = t.Coin.y + (j + .5f) * t.Pas; float aLaMarque = carte.DistanceALaMarque(x, z);
                if (t.BordEn(x, z) < .5f && aLaMarque > 3f) interieurs++; else if (aLaMarque < .5f) auBord++;
            }
            Assert.IsTrue(interieurs > 10 && auBord > 10, interieurs + " texels sur un bord intérieur loin du trait, " + auBord + " sur le trait : le trait ne suit pas le bord de la cellule seul");
            Assert.IsTrue(carte.Retirer(FormesDeTest.PAMPELUNE)); carte.Pas(5);
            Assert.IsTrue(Enumerable.Range(premier, n).All(l => Versee(l).a == 0) && carte.TeinteDuLieu(FormesDeTest.PAMPELUNE, 3) == null, "un lieu d'une cellule retirée se dessine encore");
        }
        // Le point le plus loin du bord de chaque lieu, à terre, rend sa terre et le rang de ce lieu ; la mer, rien.
        [Test] public void Le_point_au_coeur_de_chaque_lieu_rend_sa_terre_et_son_rang() {
            ServirOuest(); Poser(); Lire(1); TerrainDeCarte t = carte.Terrain; var coeurs = new int[t.NombreDeLieux]; var loin = new int[t.NombreDeLieux];
            for (int l = 0; l < coeurs.Length; l++) { coeurs[l] = -1; loin[l] = -1; }
            for (int k = 0; k < t.Lieux.Count; k++) { int l = t.Lieux[k] - 1; if (l >= 0 && t.Bords[2 * k] > loin[l]) { loin[l] = t.Bords[2 * k]; coeurs[l] = k; } }
            int justes = 0; var faux = new List<string>();
            for (int l = 0; l < coeurs.Length; l++) {
                int k = coeurs[l]; Vector3 monde = objet.transform.TransformPoint(new Vector3(t.Coin.x + (k % t.Largeur + .5f) * t.Pas, 0f, t.Coin.y + (k / t.Largeur + .5f) * t.Pas));
                long cellId = carte.Lue.Cellules[t.CelluleDuLieu(l)].CellId; var sous = carte.LieuSous(monde);
                if (carte.CelluleSous(monde)?.CellId == cellId && sous.HasValue && sous.Value.cellule.CellId == cellId && sous.Value.rang == t.RangDuLieu(l)) justes++; else faux.Add(cellId + "/" + t.RangDuLieu(l));
            }
            Assert.IsTrue(justes == t.NombreDeLieux && justes > 200, justes + " lieux justes sur " + t.NombreDeLieux + " ; faux : " + string.Join(", ", faux.Take(10)));
            Vector3 auLarge = objet.transform.TransformPoint(new Vector3(t.Coin.x + t.Pas, 0f, t.Coin.y + t.Pas));
            Assert.IsTrue(carte.CelluleSous(auLarge) == null && carte.LieuSous(auLarge) == null, "la mer est sous une terre");
        }
        [Test] public void Une_camera_donnee_n_a_pas_de_vue() {
            Servir(0, 200, Fixture); Attendue(out int servies);
            Camera donnee = new GameObject("Caméra donnée du test").AddComponent<Camera>();
            try {
                objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.camera = donnee; carte.Demarrer(); Lire(1);
                Assert.IsTrue(carte.CellulesPosees == servies && carte.Vue == null, carte.CellulesPosees + " cellules posées, vue " + (carte.Vue == null ? "absente" : "présente"));
            } finally { UnityEngine.Object.DestroyImmediate(donnee.gameObject); }
        }
    }
}
