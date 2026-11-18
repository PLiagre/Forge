using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont.Tests {
    // La carte servie se pose en un terrain d'un seul tenant, où chaque cellule servie a sa teinte, au départ la
    // couleur de sa puissance ; sans carte, le message et rien d'autre. L'attendu vient de la fixture, lue par
    // ClientCarte : les couleurs par Mailler, le terrain par celui que la carte expose.
    public sealed class CarteDessineeTests {
        private const int DELAI_MAX_PAS_MS = 100, ATTENTE_LECTURE_MS = 20000, LENTEUR_MS = 2000;
        private int port, requetes; private volatile string chemin;
        private HttpListener ecoute; private Thread fil; private GameObject objet; private CarteDessinee carte;
        private static byte[] Fixture => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); requetes = 0; chemin = null;
        }
        [TearDown] public void Fermer() {
            if (carte != null) carte.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet);
            ecoute?.Close(); ecoute = null; fil?.Join(TimeSpan.FromSeconds(5)); fil = null;
        }
        // Rend toujours la même réponse, `lenteur` ms après avoir compté la requête.
        private void Servir(int lenteur, int statut, byte[] octets) {
            ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            HttpListener auditeur = ecoute;
            fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext();
                    chemin = ctx.Request.Url.PathAndQuery; Interlocked.Increment(ref requetes); Thread.Sleep(lenteur);
                    ctx.Response.StatusCode = statut; ctx.Response.ContentLength64 = octets.Length;
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
        // La teinte versée au shader pour la cellule de ce rang servi : la case rang + 1 de la palette, la case 0 étant la mer.
        private Color32 Versee(int rang) { var palette = (Texture2D)Matiere.GetTexture("_Palette"); return palette.GetPixel((rang + 1) % palette.width, (rang + 1) / palette.width); }
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
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && chemin == "/carte", requetes + " requêtes, " + chemin);
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
            Texture cellules = mat.GetTexture("_Cellules"), relief = mat.GetTexture("_Relief"); var palette = mat.GetTexture("_Palette") as Texture2D;
            Assert.IsTrue(cellules != null && cellules.width == terrain.Largeur && cellules.height == terrain.Hauteur && cellules.filterMode == FilterMode.Point, "la grille des cellules n'est pas celle du terrain");
            Assert.IsTrue(relief != null && relief.width == terrain.LargeurDuRelief && relief.height == terrain.HauteurDuRelief, "la grille du relief n'est pas celle du terrain");
            Assert.IsTrue(palette != null && palette.width * palette.height > servies && palette.filterMode == FilterMode.Point, "la palette n'a pas une case par cellule servie, plus la mer");
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
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && carte.CellulesPosees == servies && TerrainsSousLaCarte == 1 && carte.Terrain == terrain, TerrainsSousLaCarte + " terrain(s)");
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
        // La marque couvre la teinte d'une seule cellule à la fois, et la rend comme elle est devenue en partant.
        [Test] public void La_marque_couvre_une_cellule_sans_changer_sa_teinte() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser();
            long une = lue.Cellules[10].CellId, autre = lue.Cellules[20].CellId; var rouge = new Color(0.9f, 0.1f, 0.1f, 0.5f); var rougeOpaque = new Color(0.9f, 0.1f, 0.1f, 1f); var bleu = new Color(0.1f, 0.1f, 0.9f, 1f);
            Assert.IsTrue(!carte.Marquer(une, rouge) && carte.Marquee == null, "une marque avant la pose");
            Lire(1);
            Color teinte = carte.TeinteDe(une).Value, teinteDeLAutre = carte.TeinteDe(autre).Value; Assert.IsNull(carte.Marquee);
            Assert.IsTrue(carte.Marquer(une, rouge) && carte.Marquee == une); carte.Pas(2);
            Assert.IsTrue(Proches(Versee(10), rougeOpaque), "la marque n'est pas versée, opaque, à la place de la teinte");
            Assert.IsTrue(carte.TeinteDe(une) == teinte && Proches(Versee(20), teinteDeLAutre), "la marque a changé une teinte");
            Assert.IsTrue(carte.Marquer(autre, bleu) && carte.Marquee == autre); carte.Pas(3);
            Assert.IsTrue(Proches(Versee(10), teinte) && Proches(Versee(20), bleu), "deux marques à la fois, ou la teinte couverte n'est pas revenue");
            Assert.IsTrue(!carte.Marquer(-5, rouge) && carte.Marquee == autre, "un refus a fait tomber la marque d'avant");
            var neuve = new Color(0.3f, 0.7f, 0.2f, 1f); Assert.IsTrue(carte.Teinter(autre, neuve)); carte.Pas(4);
            Assert.IsTrue(Proches(Versee(20), bleu) && carte.TeinteDe(autre) == neuve, "reteindre sous la marque l'a découverte, ou la teinte n'est pas gardée");
            carte.Demarquer(); Assert.IsNull(carte.Marquee); carte.Pas(5);
            Assert.IsTrue(Proches(Versee(20), neuve) && Proches(Versee(10), teinte), "la marque partie ne rend pas la teinte");
            // Une cellule retirée perd sa marque : la mer ne se marque pas.
            Assert.IsTrue(carte.Marquer(une, rouge) && carte.Retirer(une) && carte.Marquee == null && !carte.Marquer(une, rouge), "une cellule retirée reste marquée"); carte.Pas(6);
            Assert.AreEqual(0, Versee(10).a, "la marque d'une cellule retirée se dessine encore");
        }
        // Un éclat couvre la teinte d'autant de cellules qu'on veut, sans la changer ; la marque passe devant lui.
        [Test] public void Un_eclat_couvre_des_cellules_sans_changer_leur_teinte_et_la_marque_passe_devant() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser();
            long une = lue.Cellules[10].CellId, autre = lue.Cellules[20].CellId; var or = new Color(0.8f, 0.6f, 0.2f, 0.4f); var orOpaque = new Color(0.8f, 0.6f, 0.2f, 1f); var rouge = new Color(0.9f, 0.1f, 0.1f, 1f);
            Assert.IsTrue(!carte.Eclairer(une, or) && carte.EclatDe(une) == null, "un éclat avant la pose");
            Lire(1); Color teinte = carte.TeinteDe(une).Value, teinteDeLAutre = carte.TeinteDe(autre).Value; int maillages = objet.GetComponentsInChildren<MeshFilter>(true).Length;
            Assert.IsTrue(carte.Eclairer(une, or) && carte.Eclairer(autre, or) && !carte.Eclairer(-5, or)); carte.Pas(2);
            Assert.IsTrue(Proches(Versee(10), orOpaque) && Proches(Versee(20), orOpaque), "deux cellules éclairées ne sont pas versées à la couleur de l'éclat");
            Assert.IsTrue(carte.TeinteDe(une) == teinte && carte.TeinteDe(autre) == teinteDeLAutre && carte.EclatDe(une) == orOpaque && carte.EclatDe(lue.Cellules[30].CellId) == null, "l'éclat a changé une teinte, ou ne se relit pas");
            Assert.AreEqual(maillages, objet.GetComponentsInChildren<MeshFilter>(true).Length, "un éclat pose un maillage au-dessus du terrain");
            // La marque passe devant l'éclat, qui revient quand elle part.
            Assert.IsTrue(carte.Marquer(une, rouge)); carte.Pas(3); Assert.IsTrue(Proches(Versee(10), rouge) && Proches(Versee(20), orOpaque), "la marque ne passe pas devant l'éclat");
            carte.Demarquer(); carte.Pas(4); Assert.IsTrue(Proches(Versee(10), orOpaque), "l'éclat ne revient pas quand la marque part");
            carte.Eteindre(une); carte.Pas(5); Assert.IsTrue(Proches(Versee(10), teinte) && Proches(Versee(20), orOpaque) && carte.EclatDe(une) == null, "l'éclat éteint ne rend pas la teinte, ou éteint l'autre");
            Assert.IsTrue(carte.Retirer(autre) && carte.EclatDe(autre) == null && !carte.Eclairer(autre, or), "une cellule retirée reste éclairée"); carte.Pas(6);
            Assert.AreEqual(0, Versee(20).a, "l'éclat d'une cellule retirée se dessine encore");
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
            var lue = new CarteLue(2, new[] { Carre(7, 0), Carre(8, 10000) }); carte.Montrer(lue);
            Assert.IsTrue(carte.CellulesServies == 2 && carte.CellulesPosees == 2 && carte.Terrain != null && carte.Lue == lue && TerrainsSousLaCarte == 1, carte.CellulesPosees + " posées, " + TerrainsSousLaCarte + " terrain(s)");
            Assert.IsTrue(carte.Origine.HasValue && carte.Origine.Value.X == 10000 && carte.Origine.Value.Y == 5000, "l'origine n'est pas le centre des deux terres");
            Assert.IsTrue(carte.TexteAffiche == null && carte.Vue == null && carte.camera == null && !carte.LectureEnVol, "une carte montrée a créé une caméra, un texte ou une lecture");
            Assert.AreEqual((Color32)MaillageDeCarte.CouleurSansPuissance, (Color32)carte.TeinteDe(7).Value); Assert.IsTrue(Proches(Versee(0), MaillageDeCarte.CouleurSansPuissance) && Proches(Versee(1), MaillageDeCarte.CouleurSansPuissance));
            Assert.IsTrue(carte.CelluleSous(new Vector3(-5, 0, 0)).CellId == 7 && carte.CelluleSous(new Vector3(5, 0, 0)).CellId == 8 && carte.CelluleSous(new Vector3(50, 0, 0)) == null, "les terres ne sont pas où la carte les dessine");
            Assert.IsTrue(carte.Terrain.CelluleEn(-5, 0) == 1 && carte.Terrain.CelluleEn(5, 0) == 2 && carte.Terrain.CelluleEn(50, 0) == 0, "le terrain ne porte pas les terres à leur rang");
            TerrainDeCarte terrain = carte.Terrain; carte.Montrer(new CarteLue(1, new[] { Carre(9, 0) }));
            Assert.IsTrue(carte.Terrain == terrain && carte.CellulesServies == 2 && TerrainsSousLaCarte == 1 && carte.TeinteDe(9) == null, "une seconde carte a remplacé la première");
        }
        // Verse au shader ce qui a changé, comme le fait chaque image du jeu.
        private void Verser() => typeof(CarteDessinee).GetMethod("LateUpdate", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(carte, null);
        // L'indice de pays versé au shader pour la cellule de ce rang servi, et la couleur de liseré versée à cet indice.
        private int PaysVerse(int rang) { var table = (Texture2D)Matiere.GetTexture("_Pays"); return Mathf.RoundToInt(table.GetPixel((rang + 1) % table.width, (rang + 1) / table.width).r * 65535f); }
        private Color32 LisereVerse(int indice) { var table = (Texture2D)Matiere.GetTexture("_TeintesDesPays"); return table.GetPixel(indice % table.width, indice / table.width); }
        // Deux terres de 10 km accolées, 7 à l'ouest et 8 à l'est : leur côté commun est en x = 0, la terre va de
        // z = -5 à z = 5, et les centres des texels d'un km tombent sur les demi-entiers.
        [Test] public void La_frontiere_suit_le_pays_de_chaque_terre() {
            float loin = TerrainDeCarte.PORTEE_DES_FRONTIERES_KM; Color32 rouge = Color.red, bleu = Color.blue, vert = Color.green;
            objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>();
            Assert.IsTrue(carte.DistanceALaFrontiere(0, 0) == -1f && !carte.Rattacher(7, "a", Color.red) && carte.PaysDe(7) == null, "une carte avant la pose a des pays ou des frontières");
            carte.Montrer(new CarteLue(2, new[] { Carre(7, 0), Carre(8, 10000) }));
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
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && servies == 596 && carte.CellulesPosees == servies && carte.CellulesServies == servies, carte.TexteAffiche);
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
        [Test] public void La_camera_cadre_toute_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; Canvas toile = objet.GetComponentInChildren<Canvas>(true);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && cam != null && cam.name == "Caméra de la carte" && cam.transform.parent == objet.transform && !cam.orthographic, "caméra de la carte absente, ou pas en perspective");
            Assert.IsTrue(toile.renderMode == RenderMode.ScreenSpaceCamera && toile.worldCamera == cam, "la toile n'est pas sur la caméra de la carte");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            var coins = new[] { new Vector3(minX, 0, minZ), new Vector3(maxX, 0, minZ), new Vector3(maxX, 0, maxZ), new Vector3(minX, 0, maxZ) }; // sud-ouest, sud-est, nord-est, nord-ouest
            foreach (float aspect in new[] { 16f / 9f, 4f / 3f, 0.5f }) {
                cam.aspect = aspect; carte.Pas(2); var vus = new Vector3[4];
                for (int k = 0; k < 4; k++) {
                    vus[k] = cam.WorldToViewportPoint(objet.transform.TransformPoint(coins[k]));
                    Assert.IsTrue(vus[k].x >= 0 && vus[k].x <= 1 && vus[k].y >= 0 && vus[k].y <= 1 && vus[k].z >= cam.nearClipPlane && vus[k].z <= cam.farClipPlane, "aspect " + aspect + ", coin " + k + " hors du champ : " + vus[k].ToString("R"));
                }
                float largeur = vus[1].x - vus[0].x, hauteur = vus[3].y - vus[0].y;
                // Sous la caméra inclinée, le nord s'éloigne et se tasse : la carte couvre un peu moins du champ que vue d'en haut.
                Assert.IsTrue(largeur >= 0.85f || hauteur >= 0.85f, "aspect " + aspect + " : la carte ne couvre que " + largeur + " × " + hauteur + " du champ");
                Assert.Greater(vus[3].y, vus[0].y, "aspect " + aspect + " : le nord n'est pas en haut");
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
        // La caméra créée montre la vue que le joueur glisse et zoome : en perspective, penchée sur la carte, d'autant
        // plus qu'il s'approche, sans sortir de la carte servie. Elle n'est plus à la verticale du centre de la vue : le
        // cas juge sa pose par les rayons de l'écran, qui doivent tomber au sol là où la vue le dit.
        [Test] public void La_camera_de_la_carte_suit_la_vue_sans_sortir_de_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; cam.aspect = 16f / 9f; carte.Pas(2);
            Assert.IsNotNull(carte.Vue, "pas de vue sur une carte posée"); Assert.AreEqual(1f, carte.Vue.Echelle, "la carte ne s'ouvre pas sur toute la carte");
            Assert.IsTrue(!cam.orthographic && Mathf.Abs(cam.fieldOfView - VueDeCarte.CHAMP) < 1e-3f, "la caméra de la carte n'est pas en perspective, au champ de la vue");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            // Le point du niveau de la mer que touche le rayon de la caméra par une ancre de l'écran, en local.
            Vector2 Sol(Vector2 ancre) {
                Ray r = cam.ViewportPointToRay(new Vector3(ancre.x, ancre.y, 0)); Vector3 p = objet.transform.InverseTransformPoint(r.origin), d = objet.transform.InverseTransformDirection(r.direction);
                float t = -p.y / d.y; return new Vector2(p.x + d.x * t, p.z + d.z * t);
            }
            // Toute la carte tient dans la vue du départ : ses quatre coins, au niveau de la mer, sont à l'écran.
            foreach (var (x, z) in new[] { (minX, minZ), (maxX, minZ), (maxX, maxZ), (minX, maxZ) }) {
                Vector3 v = cam.WorldToViewportPoint(objet.transform.TransformPoint(new Vector3(x, 0f, z)));
                Assert.IsTrue(v.z > 0 && v.x >= 0 && v.x <= 1 && v.y >= 0 && v.y <= 1, "le coin (" + x + ", " + z + ") de la carte est hors de la vue du départ : " + v);
            }
            float loin = carte.Vue.Distance; Assert.AreEqual(VueDeCarte.INCLINAISON_LOIN, carte.Vue.Inclinaison, 1e-3f, "l'inclinaison sur toute la carte");
            foreach (var (crans, glisse) in new[] { (12f, new Vector2(0, 0)), (0f, new Vector2(1e7f, 1e7f)), (0f, new Vector2(-1e7f, -1e7f)), (-1000f, new Vector2(0, 0)) }) {
                carte.Vue.Zoomer(crans, new Vector2(.3f, .6f)); carte.Vue.Glisser(glisse, 900f); carte.Pas(3);
                string quand = "crans " + crans + ", glissé " + glisse; float tolerance = 3e-4f * carte.Vue.Demi;
                Assert.Less((cam.transform.position - objet.transform.TransformPoint(carte.Vue.Position)).magnitude, 5e-2f, quand + " : la caméra n'est pas là où la vue la met");
                Assert.Less(Vector3.Angle(cam.transform.forward, objet.transform.TransformDirection(carte.Vue.Regard)), 1e-2f, quand + " : la caméra ne regarde pas où la vue regarde");
                Assert.AreEqual(90f - carte.Vue.Inclinaison, Vector3.Angle(cam.transform.forward, Vector3.down), 1e-2f, quand + " : la caméra n'est pas inclinée comme la vue");
                Assert.Less((Sol(new Vector2(.5f, .5f)) - carte.Vue.Centre).magnitude, tolerance, quand + " : la caméra ne vise pas le centre de la vue");
                foreach (Vector2 ancre in new[] { new Vector2(.3f, .6f), new Vector2(.9f, .1f), new Vector2(.05f, .95f) })
                    Assert.Less((Sol(ancre) - carte.Vue.PointSous(ancre)).magnitude, tolerance, quand + " : le rayon de l'écran en " + ancre + " ne tombe pas où la vue le dit");
                if (crans < 0) { Assert.AreEqual(loin, carte.Vue.Distance, 1e-2f, "au plus loin, ce n'est plus toute la carte"); continue; }
                Assert.Less(carte.Vue.Distance, loin / 4, quand + " : la vue ne s'est pas approchée");
                Assert.IsTrue(carte.Vue.Inclinaison < VueDeCarte.INCLINAISON_LOIN - 5f && carte.Vue.Inclinaison >= VueDeCarte.INCLINAISON_PRES - 1e-3f, quand + " : la caméra ne s'incline pas en s'approchant : " + carte.Vue.Inclinaison);
                // Le rectangle visé reste dans la boîte de la carte : ses bords de gauche et de droite se lisent au sol, à mi-hauteur de l'écran.
                Vector2 gauche = Sol(new Vector2(0f, .5f)), droite = Sol(new Vector2(1f, .5f));
                Assert.IsTrue(gauche.x >= minX - tolerance && droite.x <= maxX + tolerance && carte.Vue.Centre.y - carte.Vue.Demi >= minZ - tolerance && carte.Vue.Centre.y + carte.Vue.Demi <= maxZ + tolerance,
                    quand + " : la vue sort de la carte : de " + gauche + " à " + droite);
            }
        }
        // Le terrain se dessine en relief, la mer au niveau 0 : ce que la carte pose se pose sur ce sol, et le rayon de
        // l'écran trouve le point du relief qu'il touche le premier, pas celui d'un plan. Sur les Alpes, vues de près
        // par la caméra inclinée, en 1600 × 900.
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
