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

        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Carte des villes témoin", typeof(CarteDessinee)); carte = racine.GetComponent<CarteDessinee>(); ecran = new RenderTexture(1600, ECRAN_PX, 16);
            camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.targetTexture = ecran;
            camera.orthographic = true; camera.orthographicSize = 20; camera.transform.SetPositionAndRotation(new Vector3(0, 100, 0), Quaternion.Euler(90, 0, 0)); carte.camera = camera;
            var lue = new CarteLue(3, VILLES.Select((v, k) => Carre(10 * (k + 1), 40000 * k, new VilleDeCarte(v.nom, v.habitants, new PointCarte(v.x, 20000)))).ToArray()); carte.Montrer(lue, new FormesLues(null, lue.Cellules.Select(c => new FormeDeCellule(c.CellId, c.Contour, new[] { new FormeDeLieu(0, c.Contour) }))));
            Assert.That(carte.CellulesPosees, Is.EqualTo(3), "la carte témoin n'est pas posée");
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

        [Test] public void De_loin_la_ville_la_plus_peuplee_cache_celles_qu_elle_recouvrirait()
        {
            // De près, les trois villes, à 40 km l'une de l'autre, se voient toutes avec leur nom.
            camera.orthographicSize = 20; villes.Pas();
            Assert.That(villes.Montrees, Is.EqualTo(3)); foreach (var (nom, _, _) in VILLES) Assert.That(Figurine(nom).gameObject.activeSelf && Nom(nom).gameObject.activeSelf, Is.True, nom + " est cachée de près");
            // De loin, 900 pixels pour 4 000 km : les figurines font seize pixels et les villes sont à neuf pixels l'une de l'autre.
            // Brivas, entre les deux, recouvrirait Cerda, plus peuplée qu'elle : elle se cache, avec son nom. Alba, à dix-huit pixels de Cerda, reste.
            camera.orthographicSize = 2000; villes.Pas();
            Assert.That((Figurine("Cerda").gameObject.activeSelf, Figurine("Brivas").gameObject.activeSelf, Figurine("Alba").gameObject.activeSelf), Is.EqualTo((true, false, true)), "ce n'est pas la moins peuplée des deux qui se cache");
            Assert.That((Nom("Cerda").gameObject.activeSelf, Nom("Brivas").gameObject.activeSelf, Nom("Alba").gameObject.activeSelf), Is.EqualTo((true, false, true)), "le nom d'une ville cachée reste, ou celui d'une ville montrée part");
            Assert.That(villes.Montrees, Is.EqualTo(2));
            // De deux fois plus loin, Alba aussi recouvrirait Cerda : seule la plus peuplée reste.
            camera.orthographicSize = 4000; villes.Pas();
            Assert.That(villes.Montrees, Is.EqualTo(1), "des figurines se recouvrent à l'écran");
            Assert.That((Figurine("Cerda").gameObject.activeSelf, Figurine("Brivas").gameObject.activeSelf, Figurine("Alba").gameObject.activeSelf), Is.EqualTo((true, false, false)), "ce n'est pas la plus peuplée qui reste");
            // La vue revenue, toutes reviennent.
            camera.orthographicSize = 20; villes.Pas(); Assert.That(villes.Montrees, Is.EqualTo(3), "les villes ne reviennent pas quand la vue s'approche");
            Assert.That(Nom("Alba").gameObject.activeSelf && Figurine("Alba").gameObject.activeSelf, Is.True);
        }
    }
}
