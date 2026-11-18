using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les noms courbes posés sur un sol qui n'est pas plat : chaque sommet d'une lettre est à sa place sur le sol, et
    // une grande lettre se découpe en carreaux pour le suivre. Le sol témoin est une pente ondulée, donnée au nom
    // comme la carte donne le sien ; le tracé témoin est une droite de 600 km d'ouest en est, sur une terre large de 300.
    public sealed class NomsCourbesTests
    {
        const int ECRAN_PX = 900;
        GameObject racine; Camera camera; RenderTexture ecran; NomsCourbes noms;

        static Vector3 Sol(Vector2 p) => new Vector3(p.x, 6f + 5f * Mathf.Sin(p.x / 40f) + 0.02f * p.y, p.y);

        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Noms témoins"); ecran = new RenderTexture(1600, ECRAN_PX, 16);
            camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.targetTexture = ecran;
            camera.orthographic = true; camera.transform.SetPositionAndRotation(new Vector3(0, 500, 0), Quaternion.Euler(90, 0, 0));
        }
        [TearDown] public void Fermer() { noms?.Dispose(); noms = null; camera.targetTexture = null; Object.DestroyImmediate(racine); Object.DestroyImmediate(ecran); }

        NomCourbe Ecrire(float longueur, float largeur, System.Func<Vector2, Vector3> sol)
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), sol);
            var trace = new TraceDeNom(Vector2.zero, Vector2.right, -longueur / 2f, longueur / 2f, 0f, 0f, 0f, largeur, 100);
            noms.Ecrire(new[] { ("pays-a", "Avalon", trace) }); return noms.Noms.Single();
        }
        // La vue montre `demi` km de part et d'autre du centre, et le nom s'y règle.
        void Voir(float demi) { camera.orthographicSize = demi; noms.Suivre(camera); }

        [Test] public void Une_grande_lettre_se_decoupe_en_carreaux_poses_sur_le_sol()
        {
            NomCourbe nom = Ecrire(600f, 300f, Sol);
            Assert.That(nom.Corps, Is.GreaterThan(4f * NomsCourbes.CARREAU_KM), "échantillon vide : la lettre tient dans un carreau");
            Voir(nom.Corps * ECRAN_PX / (2f * 60f)); // un corps de 60 pixels : lisible, à pleine encre
            Assert.That(nom.Opacite, Is.EqualTo(1f)); Mesh m = nom.Maillage; Vector3[] sommets = m.vertices;
            // Six lettres, chacune découpée au plus fin : sept sommets par côté.
            int cote = NomsCourbes.CARREAUX_MAX + 1;
            Assert.That(sommets.Length, Is.EqualTo(6 * cote * cote), "les lettres ne sont pas découpées en carreaux"); Assert.That(m.GetTriangles(0).Length, Is.EqualTo(6 * 6 * NomsCourbes.CARREAUX_MAX * NomsCourbes.CARREAUX_MAX));
            Assert.That(sommets.All(p => (p - Sol(new Vector2(p.x, p.z))).magnitude < 1e-3f), Is.True, "un sommet d'une lettre n'est pas posé sur le sol");
            Assert.That(sommets.Max(p => p.y) - sommets.Min(p => p.y), Is.GreaterThan(5f), "échantillon vide : le sol sous le nom est plat");
            // Les carreaux d'une lettre lisent l'atlas d'un bord à l'autre de son carré, sans trou : leurs coordonnées vont en ligne droite.
            var uv = new List<Vector2>(); m.GetUVs(0, uv);
            for (int ligne = 0; ligne < cote; ligne++)
                for (int colonne = 1; colonne + 1 < cote; colonne++)
                {
                    int k = ligne * cote + colonne;
                    Assert.That((uv[k] - (uv[k - 1] + uv[k + 1]) / 2f).magnitude, Is.LessThan(1e-5f), "les carreaux de la première lettre ne lisent pas l'atlas en ligne droite");
                    Assert.That((uv[k] - uv[k - 1]).magnitude, Is.GreaterThan(1e-5f));
                }
        }

        [Test] public void Une_petite_lettre_reste_un_seul_carre_et_sans_sol_donne_le_nom_est_a_plat()
        {
            NomCourbe petit = Ecrire(16f, 10f, Sol); Voir(petit.Corps * ECRAN_PX / (2f * 60f));
            Assert.That(petit.Corps, Is.LessThan(NomsCourbes.CARREAU_KM / 2f)); Assert.That(petit.Maillage.vertexCount, Is.EqualTo(6 * 4), "une petite lettre est découpée");
            Assert.That(petit.Maillage.vertices.All(p => (p - Sol(new Vector2(p.x, p.z))).magnitude < 1e-3f), Is.True);
            noms.Dispose(); NomCourbe plat = Ecrire(16f, 10f, null); Voir(plat.Corps * ECRAN_PX / (2f * 60f));
            Assert.That(plat.Maillage.vertices.All(p => p.y == NomsCourbes.HAUTEUR), Is.True, "sans sol donné, le nom n'est pas à plat à sa hauteur");
        }
    }
}
