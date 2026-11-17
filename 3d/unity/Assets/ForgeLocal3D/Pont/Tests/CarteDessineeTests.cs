using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
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
            // Un seul matériau, au shader du relief, qui reçoit les trois grilles du terrain et ses bornes.
            MeshRenderer rendu = sol.GetComponent<MeshRenderer>(); Material mat = rendu.sharedMaterial;
            Assert.IsTrue(rendu.sharedMaterials.Length == 1 && mat.shader.name == CarteDessinee.SHADER_DU_TERRAIN, mat.shader.name);
            Texture cellules = mat.GetTexture("_Cellules"), relief = mat.GetTexture("_Relief"); var palette = mat.GetTexture("_Palette") as Texture2D;
            Assert.IsTrue(cellules != null && cellules.width == terrain.Largeur && cellules.height == terrain.Hauteur && cellules.filterMode == FilterMode.Point, "la grille des cellules n'est pas celle du terrain");
            Assert.IsTrue(relief != null && relief.width == terrain.LargeurDuRelief && relief.height == terrain.HauteurDuRelief, "la grille du relief n'est pas celle du terrain");
            Assert.IsTrue(palette != null && palette.width * palette.height > servies && palette.filterMode == FilterMode.Point, "la palette n'a pas une case par cellule servie, plus la mer");
            Assert.AreEqual(0, ((Color32)palette.GetPixel(0, 0)).a, "la case de la mer a une teinte");
            Assert.IsTrue(mat.GetFloat("_PasDuRelief") == terrain.PasDuRelief && mat.GetFloat("_Fond") == TerrainDeCarte.FOND && mat.GetFloat("_Plafond") == TerrainDeCarte.PLAFOND, "le shader n'a pas les bornes du terrain");
            // Chaque cellule servie a la couleur de sa puissance, lue par son numéro et versée à son rang.
            var couleurs = new HashSet<Color>(); int fausses = 0;
            for (int i = 0; i < servies; i++) {
                MaillageDeCellule c = attendue.Cellules[i]; Color? teinte = carte.TeinteDe(c.CellId);
                Assert.IsTrue(teinte.HasValue, "cellule " + c.CellId + " sans teinte"); Assert.AreEqual((Color32)c.Couleur, (Color32)teinte.Value, "cellule " + c.CellId);
                if (!Proches(Versee(i), c.Couleur)) fausses++; couleurs.Add(c.Couleur);
            }
            Assert.AreEqual(0, fausses, "teintes versées différentes des couleurs attendues");
            Assert.AreEqual(40, couleurs.Count, "couleurs de puissance");
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
        // Contours, noms et caméra, avec ou sans caméra donnée. L'attendu : la carte lue par ClientCarte, l'origine de Mailler, et la conversion écrite ici.
        private CarteLue Lue(out PointCarte origine) {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence); Interlocked.Exchange(ref requetes, 0); origine = MaillageDeCarte.Mailler(lecture.Carte).Origine; return lecture.Carte;
        }
        private static Vector3 Converti(PointCarte p, PointCarte o, float y) => new Vector3((float)((p.X - o.X) / 1000), y, (float)((p.Y - o.Y) / 1000));
        private static bool Egal(Vector3 a, Vector3 b) => a.x == b.x && a.y == b.y && a.z == b.z; // `==` de Vector3 tolère un écart : on compare composante par composante
        private int Nommes(string nom) { int n = 0; foreach (Transform t in objet.GetComponentsInChildren<Transform>(true)) if (t.name == nom) n++; return n; }
        private void Contours(CarteLue lue, PointCarte o) {
            LineRenderer[] traits = objet.transform.Find("Contours de la carte").GetComponentsInChildren<LineRenderer>(true);
            int i = 0, trous = 0, points = 0, ecarts = 0;
            foreach (CelluleDeCarte c in lue.Cellules) { int rang = 0;
                foreach (PolygoneDeCarte p in c.Contour) {
                    var anneaux = new List<IReadOnlyList<PointCarte>> { p.Exterieur }; anneaux.AddRange(p.Trous); trous += p.Trous.Count;
                    foreach (IReadOnlyList<PointCarte> a in anneaux) {
                        Assert.Less(i, traits.Length, "moins de contours que d'anneaux"); LineRenderer t = traits[i++]; Assert.AreEqual("Contour " + c.CellId + "." + rang++, t.name);
                        Assert.IsTrue(!t.useWorldSpace && !t.loop && t.positionCount == a.Count, t.name + " : " + t.positionCount + " positions pour " + a.Count + " points");
                        points += a.Count; for (int k = 0; k < a.Count; k++) if (!Egal(t.GetPosition(k), Converti(a[k], o, CarteDessinee.HAUTEUR_CONTOUR))) ecarts++;
                    }
                }
            }
            Assert.IsTrue(i == traits.Length && i == 746 && trous == 71 && points == 19789, i + " anneaux dont " + trous + " trous, " + points + " points, " + traits.Length + " contours");
            Assert.AreEqual(0, ecarts, "positions différentes des points convertis");
        }
        [Test] public void Chaque_anneau_servi_a_son_contour() { Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1); Contours(lue, o);
            Assert.IsTrue(carte.CellulesPosees == 596 && TerrainsSousLaCarte == 1, TerrainsSousLaCarte + " MeshFilter sous la carte");
        }
        private void Noms(CarteLue lue, PointCarte o) {
            TextMesh[] noms = objet.transform.Find("Villes de la carte").GetComponentsInChildren<TextMesh>(true);
            var vus = new HashSet<string>(); int i = 0;
            foreach (CelluleDeCarte c in lue.Cellules)
                foreach (VilleDeCarte v in c.Villes) {
                    Assert.Less(i, noms.Length, "moins de noms que de villes"); TextMesh n = noms[i++]; vus.Add(v.Nom);
                    Assert.IsTrue(n.text == v.Nom && n.name == "Ville " + v.Nom, n.name + " pour " + v.Nom);
                    Vector3 attendu = Converti(v.Position, o, CarteDessinee.HAUTEUR_NOM); Assert.IsTrue(Egal(n.transform.localPosition, attendu),v.Nom + " en " + n.transform.localPosition.ToString("R") + ", attendu " + attendu.ToString("R"));
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
                Assert.IsTrue(p.HasValue && Egal(p.Value, noms.GetChild(i++).localPosition) && Egal(p.Value, Converti(v.Position, o, CarteDessinee.HAUTEUR_NOM)), v.Nom + " en " + p); }
            Assert.IsTrue(i == 57 && i == noms.childCount, i + " villes, " + noms.childCount + " noms");
        }
        [Test] public void La_camera_cadre_toute_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; Canvas toile = objet.GetComponentInChildren<Canvas>(true);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && cam != null && cam.name == "Caméra de la carte" && cam.transform.parent == objet.transform && cam.orthographic, "caméra de la carte absente ou mal faite");
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
                Assert.IsTrue(largeur >= 0.9f || hauteur >= 0.9f, "aspect " + aspect + " : la carte ne couvre que " + largeur + " × " + hauteur + " du champ");
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
                Contours(lue, o); Noms(lue, o); // avec une caméra donnée aussi, la carte trace ses bords et nomme ses villes
            } finally { UnityEngine.Object.DestroyImmediate(donnee.gameObject); }
        }
        // La caméra créée montre la vue que le joueur glisse et zoome, sans sortir de la carte servie.
        [Test] public void La_camera_de_la_carte_suit_la_vue_sans_sortir_de_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; cam.aspect = 16f / 9f; carte.Pas(2);
            Assert.IsNotNull(carte.Vue, "pas de vue sur une carte posée"); Assert.AreEqual(1f, carte.Vue.Echelle, "la carte ne s'ouvre pas sur toute la carte");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            float demiEnsemble = cam.orthographicSize;
            foreach (var (crans, glisse) in new[] { (12f, new Vector2(0, 0)), (0f, new Vector2(1e7f, 1e7f)), (0f, new Vector2(-1e7f, -1e7f)), (-1000f, new Vector2(0, 0)) }) {
                carte.Vue.Zoomer(crans, new Vector2(.3f, .6f)); carte.Vue.Glisser(glisse, 900f); carte.Pas(3);
                string quand = "crans " + crans + ", glissé " + glisse;
                Assert.AreEqual(carte.Vue.Demi, cam.orthographicSize, 1e-3f, quand + " : la caméra ne montre pas la vue");
                Vector3 attenduePosition = objet.transform.TransformPoint(new Vector3(carte.Vue.Centre.x, CarteDessinee.HAUTEUR_CAMERA, carte.Vue.Centre.y));
                Assert.Less((cam.transform.position - attenduePosition).magnitude, 1e-2f, quand + " : la caméra n'est pas au-dessus du centre de la vue");
                if (crans < 0) { Assert.AreEqual(demiEnsemble, cam.orthographicSize, 1e-3f, "au plus loin, ce n'est plus toute la carte"); continue; }
                Assert.Less(cam.orthographicSize, demiEnsemble / 4, quand + " : la vue ne s'est pas approchée");
                // Les quatre coins de l'écran tombent sur la boîte de la carte : la vue n'en sort pas.
                foreach (Vector2 coin in new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up }) {
                    Ray rayon = cam.ViewportPointToRay(new Vector3(coin.x, coin.y, 0)); Vector3 local = objet.transform.InverseTransformPoint(rayon.origin);
                    Assert.IsTrue(local.x >= minX - 1e-2f && local.x <= maxX + 1e-2f && local.z >= minZ - 1e-2f && local.z <= maxZ + 1e-2f, quand + " : le coin " + coin + " de l'écran est hors de la carte : " + local);
                }
            }
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
