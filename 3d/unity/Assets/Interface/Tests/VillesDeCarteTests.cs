using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les villes servies par la carte, chacune une figurine posée sur le sol. La carte témoin a trois terres carrées
    // de 40 km côte à côte, chacune avec sa ville en son milieu : 500, 5 000 et 80 000 habitants. À 40 km l'une de
    // l'autre, leurs figurines, de 5 à 9 km de rayon, ne se touchent pas.
    public sealed class VillesDeCarteTests
    {
        const int ECRAN_PX = 900;
        GameObject racine; CarteDessinee carte; VillesDeCarte villes; Camera camera; RenderTexture ecran;
        static readonly (string nom, long habitants, double x)[] VILLES = { ("Alba", 500, 20000), ("Brivas", 5000, 60000), ("Cerda", 80000, 100000) };

        [SetUp] public void Ouvrir() => Monter(VILLES);
        // La carte témoin : une terre carrée de 40 km par ville, côte à côte, chaque ville à l'abscisse donnée.
        void Monter((string nom, long habitants, double x)[] servies)
        {
            racine = new GameObject("Carte des villes témoin", typeof(CarteDessinee)); carte = racine.GetComponent<CarteDessinee>(); ecran = new RenderTexture(1600, ECRAN_PX, 16);
            camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.targetTexture = ecran;
            camera.orthographic = true; camera.orthographicSize = 20; camera.transform.SetPositionAndRotation(new Vector3(0, 100, 0), Quaternion.Euler(90, 0, 0)); carte.camera = camera;
            var lue = new CarteLue(servies.Length, servies.Select((v, k) => Carre(10 * (k + 1), 40000 * k, new VilleDeCarte(v.nom, v.habitants, new PointCarte(v.x, 20000)))).ToArray()); carte.Montrer(lue, new FormesLues(null, lue.Cellules.Select(c => new FormeDeCellule(c.CellId, c.Contour, new[] { new FormeDeLieu(0, c.Contour) }))));
            Assert.That(carte.CellulesPosees, Is.EqualTo(servies.Length), "la carte témoin n'est pas posée");
            villes = racine.AddComponent<VillesDeCarte>(); villes.Installer();
        }
        [TearDown] public void Fermer() { camera.targetTexture = null; carte.Arreter(); Object.DestroyImmediate(racine); Object.DestroyImmediate(ecran); }

        static CelluleDeCarte Carre(long id, double x, VilleDeCarte ville)
        {
            var anneau = new[] { new PointCarte(x, 0), new PointCarte(x + 40000, 0), new PointCarte(x + 40000, 40000), new PointCarte(x, 40000), new PointCarte(x, 0) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new[] { ville });
        }
        Transform Figurine(string nom) => racine.transform.Find(VillesDeCarte.RACINE + "/Figurine de " + nom);
        Transform Nom(string nom) => racine.transform.Find(VillesDeCarte.NOMS + "/Ville " + nom);

        [Test] public void La_taille_d_une_ville_suit_ses_habitants_entre_la_moins_et_la_plus_peuplee()
        {
            Assert.That((VillesDeCarte.Taille(500, 500, 80000), VillesDeCarte.Taille(80000, 500, 80000)), Is.EqualTo((1, FormesDeCarte.TAILLE_MAX)), "la moins peuplée n'est pas un bourg, ou la plus peuplée une cité");
            int avant = 0; for (long h = 500; h <= 80000; h += 500) { int t = VillesDeCarte.Taille(h, 500, 80000); Assert.That(t, Is.InRange(avant, FormesDeCarte.TAILLE_MAX), "la taille baisse quand les habitants montent, à " + h); avant = t; }
            // L'échelle est logarithmique : dix fois les habitants de la moins peuplée valent la taille du milieu.
            Assert.That(VillesDeCarte.Taille(5000, 500, 80000), Is.EqualTo(2)); Assert.That(VillesDeCarte.Taille(1200, 500, 80000), Is.EqualTo(1)); Assert.That(VillesDeCarte.Taille(40000, 500, 80000), Is.EqualTo(3));
            // Des villes toutes pareilles ont la taille du milieu ; hors des bornes, la plus proche.
            Assert.That((VillesDeCarte.Taille(700, 700, 700), VillesDeCarte.Taille(100, 500, 80000), VillesDeCarte.Taille(900000, 500, 80000)), Is.EqualTo((2, 1, FormesDeCarte.TAILLE_MAX)));
        }

        [Test] public void Chaque_ville_servie_a_sa_figurine_sur_le_sol_a_la_taille_de_ses_habitants()
        {
            villes.Pas(); Assert.That(villes.Posees, Is.EqualTo(3)); Assert.That(racine.transform.Find(VillesDeCarte.RACINE).childCount, Is.EqualTo(3));
            Color cuivre = SocleInterface.Couleur("cuivre"); cuivre.a = 1f; Material matiere = null; int taille = 0;
            foreach (var (nom, habitants, x) in VILLES)
            {
                Transform f = Figurine(nom); Assert.That(f, Is.Not.Null, "pas de figurine pour " + nom); taille++;
                Assert.That((f.localPosition - carte.PositionSurLaCarte(new PointCarte(x, 20000), 0f).Value).magnitude, Is.LessThan(1e-4f), nom + " n'est pas posée sur le sol à sa place");
                Assert.That(f.GetComponent<MeshFilter>().sharedMesh.name, Is.EqualTo("Bourg de taille " + taille), nom + " n'a pas la taille de ses " + habitants + " habitants");
                var rendu = f.GetComponent<MeshRenderer>(); Assert.That((Color32)rendu.sharedMaterial.color, Is.EqualTo((Color32)cuivre), "les toits de " + nom + " ne sont pas au cuivre du socle");
                Assert.That(rendu.sharedMaterial.shader.name, Is.EqualTo(FormesDeCarte.SHADER)); if (matiere == null) matiere = rendu.sharedMaterial; Assert.That(rendu.sharedMaterial, Is.SameAs(matiere), "les villes ne partagent pas leur matériau");
                Assert.That(f.GetComponent<Collider>(), Is.Null);
            }
            // Un second passage ne repose rien.
            Transform alba = Figurine("Alba"); villes.Pas(); Assert.That(Figurine("Alba"), Is.SameAs(alba)); Assert.That(racine.transform.Find(VillesDeCarte.RACINE).childCount, Is.EqualTo(3));
        }

        [Test] public void De_loin_la_figurine_garde_sa_taille_a_l_ecran_et_le_nom_se_range_au_sud_d_elle()
        {
            // De près : 900 pixels pour 40 km, un bourg de 10 km en fait 225 ; il garde sa taille.
            camera.orthographicSize = 20; villes.Pas(); Transform alba = Figurine("Alba"), nom = Nom("Alba"); float rayon = FormesDeCarte.RayonDuBourg(1);
            Assert.That(nom, Is.Not.Null, "la carte n'a pas nommé Alba"); Assert.That(alba.localScale, Is.EqualTo(Vector3.one), "de près, la figurine est grossie");
            float kmParPixel = 40f / ECRAN_PX; Assert.That(alba.localPosition.z - nom.localPosition.z, Is.EqualTo(rayon + VillesDeCarte.MARGE_DU_NOM_PX * kmParPixel).Within(1e-3f), "le nom n'est pas rangé au sud du socle");
            Assert.That(nom.localPosition.x, Is.EqualTo(alba.localPosition.x).Within(1e-4f)); Assert.That(nom.localPosition.y, Is.EqualTo(carte.SurLeSol(nom.localPosition.x, nom.localPosition.z, CarteDessinee.HAUTEUR_NOM).y).Within(1e-4f), "le nom n'est pas au-dessus du sol");
            // De loin : 900 pixels pour 4 000 km ; la figurine est grossie jusqu'à sa taille minimale, et le nom s'écarte avec elle.
            camera.orthographicSize = 2000; villes.Pas(); kmParPixel = 4000f / ECRAN_PX; float echelle = alba.localScale.x;
            Assert.That(2f * rayon * echelle / kmParPixel, Is.EqualTo(VillesDeCarte.MIN_PX).Within(1e-2f), "de loin, la figurine n'a pas sa taille minimale à l'écran"); Assert.That(echelle, Is.GreaterThan(5f));
            Assert.That(alba.localPosition.z - nom.localPosition.z, Is.EqualTo(rayon * echelle + VillesDeCarte.MARGE_DU_NOM_PX * kmParPixel).Within(1e-2f), "de loin, le nom n'est plus au sud du socle");
            // La vue revenue, la figurine reprend sa taille.
            camera.orthographicSize = 20; villes.Pas(); Assert.That(alba.localScale, Is.EqualTo(Vector3.one));
        }

        // De près, les trois villes, à 40 km l'une de l'autre, se voient toutes avec leur nom. De trop loin, aucune n'est une
        // capitale : toutes se cachent, et reviennent quand la vue s'approche.
        [Test] public void De_loin_seules_les_capitales_restent_et_les_villes_reviennent_de_pres()
        {
            camera.orthographicSize = 20; villes.Pas();
            Assert.That(villes.Montrees, Is.EqualTo(3)); foreach (var (nom, _, _) in VILLES) Assert.That(Figurine(nom).gameObject.activeSelf && Nom(nom).gameObject.activeSelf, Is.True, nom + " est cachée de près");
            // Juste en deçà du seuil, les villes se montrent encore ; au-delà, elles se cachent avec leur nom.
            camera.orthographicSize = 0.95f * VillesDeCarte.KM_PAR_PIXEL_DES_VILLES * ECRAN_PX / 2f; villes.Pas(); Assert.That(villes.Montrees, Is.EqualTo(3), "en deçà du seuil, une ville se cache");
            camera.orthographicSize = 1.05f * VillesDeCarte.KM_PAR_PIXEL_DES_VILLES * ECRAN_PX / 2f; villes.Pas();
            Assert.That(villes.Montrees, Is.Zero, "de loin, une ville qui n'est pas une capitale se montre");
            foreach (var (nom, _, _) in VILLES) Assert.That(Figurine(nom).gameObject.activeSelf || Nom(nom).gameObject.activeSelf, Is.False, nom + " se montre de loin");
            camera.orthographicSize = 20; villes.Pas(); Assert.That(villes.Montrees, Is.EqualTo(3), "les villes ne reviennent pas quand la vue s'approche");
        }

        // Deux villes à 8 km l'une de l'autre, de part et d'autre d'une frontière de terres : vues à un km par pixel, leurs
        // figurines de seize pixels se recouvriraient : la moins peuplée se cache avec son nom.
        [Test] public void La_ville_la_plus_peuplee_cache_celle_qu_elle_recouvrirait()
        {
            Fermer(); Monter(new[] { ("Alba", 500L, 36000.0), ("Cerda", 80000L, 44000.0) });
            camera.orthographicSize = ECRAN_PX / 2f; villes.Pas(); Assert.That(VillesDeCarte.KM_PAR_PIXEL_DES_VILLES, Is.GreaterThan(1f), "échantillon vide : les villes sont cachées à cette distance");
            Assert.That((Figurine("Cerda").gameObject.activeSelf, Figurine("Alba").gameObject.activeSelf), Is.EqualTo((true, false)), "ce n'est pas la moins peuplée des deux qui se cache");
            Assert.That((Nom("Cerda").gameObject.activeSelf, Nom("Alba").gameObject.activeSelf), Is.EqualTo((true, false)), "le nom d'une ville cachée reste, ou celui d'une ville montrée part");
            Assert.That(villes.Montrees, Is.EqualTo(1));
        }

        // Un port posé sur la mer, à 3 km de la côte de sa terre, comme Constantinople déborde sur la mer de Marmara : sa
        // figurine répond sur tout ce qu'elle couvre, son pied compris, par le lieu de sa terre ; au-delà, la mer reste la mer.
        [Test] public void Une_ville_cotiere_repond_sur_toute_sa_figurine_meme_sur_la_mer()
        {
            Fermer(); Monter(new[] { ("Alba", 500L, 20000d), ("Brivas", 5000L, 60000d), ("Port", 80000L, 123000d) });
            villes.Pas(); var port = villes.Figurines.Single(f => f.ville == "Port");
            Vector3 Monde(Vector3 local) => racine.transform.TransformPoint(local);
            Assert.That(port.montree && port.rayonKm > 3.5f, Is.True, "échantillon faussé : la figurine du port est cachée ou ne couvre pas la côte (" + port.rayonKm + " km)");
            Assert.That(carte.Terrain.CelluleEn(port.pied.x, port.pied.z), Is.EqualTo((ushort)0), "échantillon faussé : le pied du port n'est pas sur la mer");
            int points = 0;
            for (int k = -1; k < 8; k++)
            {
                Vector3 ici = port.pied + (k < 0 ? Vector3.zero : new Vector3(Mathf.Cos(k * Mathf.PI / 4f), 0f, Mathf.Sin(k * Mathf.PI / 4f)) * .9f * port.rayonKm);
                var lieu = carte.LieuSous(Monde(ici)); points++;
                Assert.That(lieu.HasValue && lieu.Value.cellule.CellId == 30 && lieu.Value.rang == 0, Is.True, "sous la figurine du port, en " + ici + ", " + (lieu.HasValue ? "la terre " + lieu.Value.cellule.CellId : "la mer"));
            }
            Assert.That(points, Is.EqualTo(9), "échantillon vide");
            // Contre-épreuve : à 5 km au-delà de la figurine, la mer ; et une figurine cachée ne couvre rien.
            Assert.That(carte.LieuSous(Monde(port.pied + Vector3.right * (port.rayonKm + 5f))), Is.Null, "au-delà de la figurine, la mer rend un lieu");
            carte.Ancrer(new object(), port.pied, 30, 0f); Assert.That(carte.LieuSous(Monde(port.pied + Vector3.right * (port.rayonKm + 5f))), Is.Null, "une ancre de rayon nul couvre la mer");
        }
    }

    // Les capitales sur l'Europe entière relevée du vrai service : le siège de la maison de chaque pays tenant, servi par
    // `/jouables`, est une ville de `/carte` ou un siège de `/atlas` ; sinon il se déclare.
    public sealed class VillesDeCarteEuropeTests
    {
        EuropeDeCarte europe;
        [OneTimeSetUp] public void Poser() => europe = new EuropeDeCarte();
        [OneTimeTearDown] public void Fermer() => europe?.Dispose();
        static TerresDeLaCarte Terres => Forge.Pont.Tests.EuropeDeTest.TerresEurope;

        // Chaque ville servie et chaque capitale posée, vue de près (150 km de demi-hauteur), répond au survol et au clic sur
        // tout ce que sa figurine couvre : son pied et huit points à neuf dixièmes de son rayon rendent un lieu. Au large de la
        // mer Ionienne, loin de toute figurine, la mer reste la mer.
        [Test] public void Chaque_ville_et_chaque_capitale_repond_sous_toute_sa_figurine()
        {
            Camera camera = europe.Carte.camera; Vector3 avant = camera.transform.position; float taille = camera.orthographicSize;
            var muettes = new List<string>(); int jugees = 0, cachees = 0; var toutes = europe.Villes.Figurines.ToList();
            try
            {
                foreach (var f0 in toutes)
                {
                    camera.transform.position = new Vector3(f0.pied.x, 5000f, f0.pied.z); camera.orthographicSize = 150f; europe.Villes.Pas();
                    var f = europe.Villes.Figurines.First(x => x.ville == f0.ville && x.pied == f0.pied);
                    if (!f.montree) { cachees++; continue; }
                    jugees++;
                    for (int k = -1; k < 8; k++)
                    {
                        Vector3 ici = f.pied + (k < 0 ? Vector3.zero : new Vector3(Mathf.Cos(k * Mathf.PI / 4f), 0f, Mathf.Sin(k * Mathf.PI / 4f)) * .9f * f.rayonKm);
                        if (europe.Carte.LieuSous(europe.Racine.transform.TransformPoint(ici)) == null) { muettes.Add(f.ville + (k < 0 ? " (pied)" : " (vers " + k * 45 + "°)")); }
                    }
                }
            }
            finally { camera.transform.position = avant; camera.orthographicSize = taille; europe.Villes.Pas(); }
            Assert.That(toutes.Count, Is.GreaterThan(57), "échantillon vide : ni les villes de la carte ni les capitales de l'atlas");
            Assert.That(jugees, Is.GreaterThanOrEqualTo(toutes.Count * 8 / 10), cachees + " figurines cachées de près sur " + toutes.Count);
            Assert.That(muettes, Is.Empty, muettes.Count + " points muets sous une figurine : " + string.Join(", ", muettes.Take(20)));
            // Contre-épreuve : la mer Ionienne, à plus de 100 km de toute figurine, ne rend aucun lieu.
            Vector2 ionienne = europe.Ici(new PointCarte(5030000, 1545000));
            Assert.That(toutes.Min(f => Vector2.Distance(ionienne, new Vector2(f.pied.x, f.pied.z))), Is.GreaterThan(100f), "échantillon faussé : une figurine est près de la mer Ionienne");
            Assert.That(europe.Carte.LieuSous(europe.Racine.transform.TransformPoint(new Vector3(ionienne.x, 0f, ionienne.y))), Is.Null, "la mer Ionienne rend un lieu");
        }

        // La capitale attendue de chaque pays tenant, lue dans les réponses figées : son nom et sa place en km locaux ; null si son siège ne se place pas.
        Dictionary<string, (string nom, Vector2 place)?> Attendues(JouablesLus jouables)
        {
            var fiches = jouables.Fiches.ToDictionary(f => f.Id); var sieges = Forge.Pont.Tests.EuropeDeTest.AtlasEurope.Sieges.ToDictionary(s => s.Maison);
            var tenants = new HashSet<string>(Terres.Terres.Select(t => t.Pays).Where(p => p != null)); var attendues = new Dictionary<string, (string, Vector2)?>();
            foreach (var pays in Terres.Pays.Where(p => tenants.Contains(p.Id)))
            {
                string maison = pays.Maison?.Id; SiegeJouable siege = maison != null && fiches.TryGetValue(maison, out FicheJouable f) ? f.Siege : null;
                var carte = Forge.Pont.Tests.EuropeDeTest.CarteEurope; var deCeNom = siege == null ? new VilleDeCarte[0] : carte.Cellules.SelectMany(c => c.Villes).Where(v => v.Nom == siege.Nom).ToArray();
                VilleDeCarte ville = siege?.CellId == null ? null : carte.Cellules.Single(c => c.CellId == siege.CellId).Villes.FirstOrDefault(v => v.Nom == siege.Nom) ?? (deCeNom.Length == 1 ? deCeNom[0] : null);
                attendues[pays.Id] = ville != null ? (ville.Nom, europe.Ici(ville.Position)) : maison != null && sieges.TryGetValue(maison, out SiegeDeLAtlas s) ? (s.Nom, europe.Ici(s.Point)) : ((string, Vector2)?)null;
            }
            return attendues;
        }
        (string nom, Vector3 pied, IReadOnlyList<string> pays, TextMesh texte, Transform figurine) CapitaleDe(string pays) => europe.Villes.Capitales.Single(c => c.pays.Contains(pays));

        [Test] public void Chaque_pays_tenant_a_sa_capitale_marquee_et_nommee_ou_declaree()
        {
            var attendues = Attendues(Forge.Pont.Tests.EuropeDeTest.JouablesEurope); var placees = attendues.Where(a => a.Value != null).ToList();
            Assert.That(placees.Count, Is.GreaterThan(50), "échantillon vide : trop peu de capitales servies");
            Assert.That(europe.Villes.Capitales.Count, Is.EqualTo(placees.Select(a => a.Value.Value.nom + a.Value.Value.place).Distinct().Count()), "le compte des capitales posées n'est pas celui des sièges servis sur la carte");
            foreach (var (pays, attendue) in placees)
            {
                var c = CapitaleDe(pays);
                Assert.That((c.nom, (new Vector2(c.pied.x, c.pied.z) - attendue.Value.place).magnitude < 1e-2f), Is.EqualTo((attendue.Value.nom, true)), pays + " n'a pas sa capitale au siège servi");
                Assert.That(c.figurine.GetComponent<MeshFilter>().sharedMesh.name, Does.StartWith("Capitale de taille"), pays + " : sa capitale n'est pas marquée");
                Assert.That(c.texte != null && c.texte.text == attendue.Value.nom, Is.True, pays + " : sa capitale n'est pas nommée");
            }
            var marquees = new HashSet<Transform>(europe.Villes.Capitales.Select(c => c.figurine));
            var autres = europe.Racine.transform.Find(VillesDeCarte.RACINE).Cast<Transform>().Where(f => !marquees.Contains(f)).ToList();
            Assert.That(autres, Is.Not.Empty, "échantillon vide : toutes les villes sont des capitales"); Assert.That(autres.All(f => f.GetComponent<MeshFilter>().sharedMesh.name.StartsWith("Bourg")), Is.True, "une ville qui n'est pas une capitale en porte la marque");
            Assert.That(europe.Villes.Capitales.Any(c => c.figurine.parent == europe.Racine.transform.Find(VillesDeCarte.RACINE) && c.texte.transform.parent.name == VillesDeCarte.NOMS), Is.True, "échantillon vide : aucune capitale n'est une ville de la carte");
            // Un siège qui ne se place pas se déclare, avec sa raison, et la légende le dit.
            Assert.That(europe.Villes.Introuvables.Select(i => i.pays), Is.EquivalentTo(attendues.Where(a => a.Value == null).Select(a => a.Key)), "les sièges déclarés introuvables ne sont pas ceux qu'aucune réponse ne place");
            Assert.That(europe.Villes.Introuvables.All(i => !string.IsNullOrEmpty(i.raison)), Is.True);
            europe.Peindre(); europe.Peindre();
            Assert.That(europe.Calques.Legende.GetComponentInParent<Infobulle>().Phrase, Does.Contain("Capitales non placées, faute de siège servi sur la carte : " + europe.Villes.Introuvables.Count + " pays"));
        }

        // Le siège de la Castille est servi « Tolède » dans une cellule voisine de la ville : la ville de ce nom, seule sur la carte, est sa capitale.
        [Test] public void Un_siege_servi_dans_une_cellule_voisine_de_sa_ville_la_retrouve_par_son_nom()
        {
            string castille = Terres.Pays.Single(p => p.Nom == "Castille").Id; var fiche = Forge.Pont.Tests.EuropeDeTest.JouablesEurope.Fiches.Single(f => f.Id == Terres.MaisonDuPays(castille).Id);
            Assert.That(Forge.Pont.Tests.EuropeDeTest.CarteEurope.Cellules.Single(c => c.CellId == fiche.Siege.CellId).Villes.Any(v => v.Nom == fiche.Siege.Nom), Is.False, "échantillon vide : le siège de la Castille est dans la cellule de sa ville");
            Assert.That(CapitaleDe(castille).nom, Is.EqualTo("Tolède"));
        }

        [Test] public void Biskra_est_marquee_et_nommee_au_siege_de_l_atlas()
        {
            SiegeDeLAtlas biskra = Forge.Pont.Tests.EuropeDeTest.AtlasEurope.Sieges.Single(s => s.Nom == "Biskra");
            string zab = Terres.Pays.Single(p => p.Maison?.Id == biskra.Maison).Id; var c = CapitaleDe(zab);
            Assert.That(c.nom, Is.EqualTo("Biskra")); Assert.That((new Vector2(c.pied.x, c.pied.z) - europe.Ici(biskra.Point)).magnitude, Is.LessThan(1e-2f), "Biskra n'est pas au point de son siège");
            Assert.That(c.texte.text, Is.EqualTo("Biskra")); Assert.That(c.figurine.GetComponent<MeshFilter>().sharedMesh.name, Does.StartWith("Capitale de taille"));
            // Vue de près, Biskra se montre avec son nom.
            europe.Voir(new Vector2(c.pied.x, c.pied.z), 150f);
            Assert.That(c.figurine.gameObject.activeSelf, Is.True, "la figurine de Biskra est cachée");
            Assert.That(europe.Calques.EtiquetteDe(c.texte)?.enabled, Is.True, "le nom de Biskra n'est pas montré");
        }

        // Une capitale passe avant les villes et devant le nom d'un pays : le nom se pose à côté d'elle, et aucune capitale nommée
        // n'est sous une lettre d'un nom de pays lisible.
        [Test] public void Une_capitale_montree_ne_recouvre_pas_un_nom_de_pays_lisible()
        {
            Vector2 Ici(string pays) { var c = CapitaleDe(pays); return new Vector2(c.pied.x, c.pied.z); }
            int montrees = 0;
            foreach (var (centre, demi) in new[] { (Vector2.zero, 1500f), (Ici("puissance-3"), 450f), (Ici("puissance-10"), 400f), (Ici(Terres.Pays.Single(p => p.Nom == "Émirat du Zab").Id), 300f) })
            {
                europe.Voir(centre, demi);
                var lettres = europe.LettresDesPays(); montrees += europe.Calques.PlacesDesCapitales.Count;
                foreach (Rect capitale in europe.Calques.PlacesDesCapitales) Assert.That(lettres.Any(l => l.Overlaps(capitale)), Is.False, "une capitale s'écrit sur un nom de pays lisible, demi " + demi);
                foreach (Rect ville in europe.Calques.PlacesDesVilles.Except(europe.Calques.PlacesDesCapitales)) Assert.That(europe.Calques.PlacesDesCapitales.Any(c => c.Overlaps(ville)), Is.False, "une ville s'écrit sur une capitale");
            }
            Assert.That(montrees, Is.GreaterThan(0), "échantillon vide : aucune capitale montrée");
            // Paris, capitale de la France, se montre sur la vue de la France.
            europe.Voir(Ici("puissance-3"), 450f); Assert.That(europe.Calques.EtiquetteDe(CapitaleDe("puissance-3").texte)?.enabled, Is.True, "la capitale de la France n'est pas nommée sur sa vue");
        }

        // Le cadre d'un pays : ses terres, sans celles qui sont loin du gros (Caffa, que tient Gênes), et sa capitale, qui peut être hors
        // d'elles (Barcelone, siège de la maison de la Sicile) ; avec assez de recul pour que son nom s'y lise, son corps au plus à
        // `PART_DE_L_ECRAN` de la hauteur de l'écran.
        const float PART_DE_L_ECRAN = 0.06f, ASPECT = 1600f / EuropeDeCarte.ECRAN_PX;
        (Vector2 centre, float demi) Cadre(string pays, float corps, Vector2 capitale)
        {
            var cellules = europe.Carte.Lue.Cellules.Where(c => Terres.PaysDe(c.CellId) == pays).ToList(); Assert.That(cellules, Is.Not.Empty, pays + " ne tient aucune terre");
            Vector2 Centre(CelluleDeCarte c) => europe.Ici(c.Contour[0].Exterieur[0]);
            var xs = cellules.Select(c => Centre(c).x).OrderBy(x => x).ToList(); var zs = cellules.Select(c => Centre(c).y).OrderBy(z => z).ToList();
            var median = new Vector2(xs[xs.Count / 2], zs[zs.Count / 2]); var distances = cellules.Select(c => (Centre(c) - median).magnitude).OrderBy(d => d).ToList();
            float portee = 1.6f * distances[Mathf.Min(distances.Count - 1, (int)(0.8f * distances.Count))] + 1f;
            var points = cellules.Where(c => (Centre(c) - median).magnitude <= portee).SelectMany(c => c.Contour.SelectMany(p => p.Exterieur)).Select(europe.Ici).ToList(); points.Add(capitale);
            Vector2 min = new Vector2(points.Min(p => p.x), points.Min(p => p.y)), max = new Vector2(points.Max(p => p.x), points.Max(p => p.y));
            float demi = Mathf.Max((max.y - min.y) / 2f, (max.x - min.x) / 2f / ASPECT) * 1.06f;
            return ((min + max) / 2f, Mathf.Max(demi, corps / (2f * PART_DE_L_ECRAN)));
        }
        // La place qu'aurait l'étiquette d'une capitale à l'écran, comme les calques la posent : centrée sur son nom posé.
        Rect PlaceDeLEtiquette(TextMesh texte, UnityEngine.UI.Text etiquette)
        {
            Vector3 ecran = europe.Carte.camera.WorldToScreenPoint(texte.transform.position); float largeur = etiquette.preferredWidth, hauteur = 1.3f * etiquette.fontSize;
            return new Rect(ecran.x - largeur / 2f - 3f, ecran.y - hauteur / 2f - 2f, largeur + 6f, hauteur + 4f);
        }

        // Chaque pays vu à l'échelle où il remplit l'écran, ou d'assez loin pour que son nom se lise : sa capitale y est nommée, et son nom
        // se lit encore. La capitale passe devant le nom d'un pays plus petit que lui, qui se pose à côté d'elle ou se réduit. Seule
        // exception, comptée : une capitale qu'une autre capitale montrée recouvre. La Navarre, plus petite que son nom, en est la contre-épreuve.
        const string NAVARRE = "puissance-7";
        [Test] public void La_capitale_de_chaque_pays_se_lit_quand_le_pays_remplit_l_ecran()
        {
            var noms = europe.Guerre.NomsDesPays.ToDictionary(n => n.Pays); var tenants = new HashSet<string>(Terres.Terres.Select(t => t.Pays).Where(p => p != null));
            var pays = Terres.Pays.Select(p => p.Id).Where(id => tenants.Contains(id) && noms.ContainsKey(id) && europe.Villes.Capitales.Any(c => c.pays.Contains(id))).OrderBy(id => id, System.StringComparer.Ordinal).ToList();
            Assert.That(pays.Count, Is.GreaterThan(50), "échantillon vide : trop peu de pays nommés à la capitale placée"); Assert.That(pays, Does.Contain(NAVARRE), "échantillon vide : la Navarre n'a pas de capitale placée");
            var fautes = new List<string>(); var couvertes = new List<string>(); int deplaces = 0;
            foreach (string id in pays)
            {
                NomCourbe nom = noms[id]; var c = CapitaleDe(id); var (centre, demi) = Cadre(id, europe.Guerre.Ecriture.CorpsDOrigine(nom), new Vector2(c.pied.x, c.pied.z)); europe.Voir(centre, demi);
                var etiquette = europe.Calques.EtiquetteDe(c.texte); bool nommee = etiquette != null && etiquette.enabled;
                if (!nommee && etiquette != null && (!c.figurine.gameObject.activeInHierarchy || europe.Calques.PlacesDesCapitales.Any(r => r.Overlaps(PlaceDeLEtiquette(c.texte, etiquette)))))
                { couvertes.Add(Terres.NomDuPays(id) + " (" + c.nom + ")"); continue; }
                bool lisible = !nom.Masque && nom.Opacite > 0f;
                // Un nom qui s'écarte de sa capitale reste sur la terre de son pays : il ne s'écrit jamais sur un voisin.
                if (europe.Guerre.Ecriture.VarianteDe(nom) != (0, 0f))
                {
                    deplaces++; TerrainDeCarte terrain = europe.Carte.Terrain; int dehors = 0;
                    for (int i = 0; i < nom.Ecrit.Length; i++)
                    {
                        if (char.IsWhiteSpace(nom.Ecrit[i])) continue; Vector2 p = nom.Compose.Lettres[i].Point; ushort n = terrain.LieuEn(p.x, p.y);
                        if (n == 0 || Terres.PaysDe(europe.Carte.Lue.Cellules[terrain.CelluleDuLieu(n - 1)].CellId) != id) dehors++;
                    }
                    if (dehors > NomsCourbes.LETTRES_HORS_DE_SA_TERRE) fautes.Add(Terres.NomDuPays(id) + " : son nom écarté de " + c.nom + " a " + dehors + " lettres hors de sa terre");
                }
                if (!nommee || !lisible) fautes.Add(Terres.NomDuPays(id) + " à " + demi.ToString("0") + " km : " + (nommee ? "" : c.nom + " non nommée ; ") + (lisible ? "nom lisible" : "nom illisible") + " (" + nom.CorpsPx.ToString("0") + " px)");
            }
            Assert.That(deplaces, Is.GreaterThan(0), "échantillon vide : aucun nom ne s'est écarté de sa capitale");
            TestContext.WriteLine(pays.Count + " pays vus, " + deplaces + " noms écartés de leur capitale, " + couvertes.Count + " capitales couvertes par une autre : " + string.Join(", ", couvertes));
            Assert.That(fautes, Is.Empty, fautes.Count + " pays sur " + pays.Count + " : " + string.Join(" ; ", fautes));
            Assert.That(couvertes.Count, Is.LessThan(pays.Count / 5), "trop de capitales couvertes par une autre : " + string.Join(", ", couvertes));
            Assert.That(couvertes.Any(n => n.StartsWith(Terres.NomDuPays(NAVARRE))), Is.False, "Pampelune est couverte par une autre capitale : la contre-épreuve ne prouve rien");
        }

        // Sans siège servi pour sa maison, l'Angleterre n'a pas de capitale : Londres ne se devine pas, elle se déclare.
        [Test] public void Un_siege_absent_se_declare_au_lieu_de_se_deviner()
        {
            string angleterre = "puissance-1", maison = Terres.MaisonDuPays(angleterre).Id; JouablesLus tous = Forge.Pont.Tests.EuropeDeTest.JouablesEurope;
            Assert.That(CapitaleDe(angleterre).nom, Is.EqualTo("Londres"), "échantillon vide : l'Angleterre n'a pas Londres pour capitale");
            var sans = new JouablesLus(tous.Tick, tous.Date, tous.Fiches.Where(f => f.Id != maison));
            try
            {
                europe.Villes.Brancher(() => sans, europe.Guerre, europe.Atlas); europe.Villes.Pas();
                Assert.That(europe.Villes.Capitales.Any(c => c.pays.Contains(angleterre)), Is.False, "Londres est devinée capitale sans siège servi");
                Assert.That(europe.Villes.Introuvables.Single(i => i.pays == angleterre).raison, Is.EqualTo("maison sans siège servi"));
                Assert.That(europe.Racine.transform.Find(VillesDeCarte.RACINE + "/Figurine de Londres").GetComponent<MeshFilter>().sharedMesh.name, Does.StartWith("Bourg"), "Londres garde la marque d'une capitale");
            }
            finally { europe.Villes.Brancher(() => tous, europe.Guerre, europe.Atlas); europe.Villes.Pas(); }
            Assert.That(CapitaleDe(angleterre).nom, Is.EqualTo("Londres"), "la capitale ne revient pas avec son siège");
        }
    }
}
