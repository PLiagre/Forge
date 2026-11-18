using System;
using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont {
    // Les figurines posées sur la carte, faites par le code : un bourg (des maisons à pignon autour d'une église, et
    // des remparts quand il est grand) et une armée (une bannière, puis un carré de piquiers en marche ou des tentes
    // au siège). Chacune tient sur un socle, comme un pion : son dessus se lit de loin comme un disque de couleur, son
    // bord sombre la détache du terrain et descend sous son pied pour cacher la pente. Un seul maillage par figurine,
    // à facettes, en km de la carte, son centre au pied du socle.
    // La couleur est par sommet : celle de la pierre, du bois ou du métal, donnée telle quelle ; une couleur absente
    // dit une part teintée, dont les sommets, d'alpha 1, prennent la teinte du matériau — celle du maître d'un lieu
    // sur le dessus de son socle, celle du pays d'une armée sur son socle et son étoffe. Du décor : aucune forme ne
    // dit un nombre du monde, et la même figurine demandée deux fois est la même.
    public static class FormesDeCarte {
        public const string SHADER = "Forge/FormeDeCarte";
        // La plus grande taille d'un bourg ; le rayon du socle de chaque taille, et de celui d'une armée, en km.
        public const int TAILLE_MAX = 3; public const float RAYON_DE_L_ARMEE_KM = 5.5f, HAUTEUR_DU_SOCLE_KM = 0.3f;
        private static readonly float[] RAYONS = { 3.2f, 5f, 7f, 9f };
        private static readonly int[] MAISONS = { 3, 8, 13, 20 };
        public static float RayonDuBourg(int taille) => RAYONS[Mathf.Clamp(taille, 0, TAILLE_MAX)];

        // Un matériau de figurine à cette teinte ; faute du shader des figurines, celui de base, d'une seule couleur.
        public static Material Matiere(Color teinte) {
            Shader shader = Resources.Load<Shader>(SHADER); teinte.a = 1f;
            return shader != null ? new Material(shader) { color = teinte } : new Material(MateriauDeBase.Prendre()) { color = teinte };
        }

        // L'échelle qui garde une figurine d'au moins `minPx` pixels de large à l'écran, là où elle est ; 1 quand elle
        // les fait déjà, ou derrière la caméra.
        public static float EchellePourLEcran(Camera camera, Vector3 monde, float rayonKm, float minPx) {
            if (camera == null || rayonKm <= 0f) return 1f;
            Transform c = camera.transform; float profondeur = Vector3.Dot(monde - c.position, c.forward);
            if (!camera.orthographic && profondeur <= camera.nearClipPlane) return 1f;
            float pixelsParKm = camera.pixelHeight / (camera.orthographic ? 2f * camera.orthographicSize : 2f * profondeur * Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad / 2f));
            return Mathf.Max(1f, minPx / (2f * rayonKm * pixelsParKm));
        }
        // Ce qu'un pixel de l'écran couvre de km là où est ce point ; 0 derrière la caméra.
        public static float KmParPixel(Camera camera, Vector3 monde) {
            if (camera == null) return 0f;
            Transform c = camera.transform; float profondeur = Vector3.Dot(monde - c.position, c.forward);
            if (!camera.orthographic && profondeur <= camera.nearClipPlane) return 0f;
            return (camera.orthographic ? 2f * camera.orthographicSize : 2f * profondeur * Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad / 2f)) / camera.pixelHeight;
        }

        // Un bourg de la taille donnée, de 0 (un hameau de trois maisons) à `TAILLE_MAX` (une cité dans ses remparts) : ses
        // murs de `pierre`, le bord de son socle de la couleur `bord` ; ses toits et le dessus de son socle de la couleur
        // donnée, ou teintés quand elle est absente.
        public static Mesh Bourg(int taille, Color pierre, Color bord, Color? toits, Color? dessus) {
            taille = Mathf.Clamp(taille, 0, TAILLE_MAX); var c = new Chantier(); float rayon = RAYONS[taille];
            c.Socle(rayon, dessus, bord);
            float dedans = taille >= 2 ? rayon - 2.5f : rayon - 1.4f; int maisons = MAISONS[taille];
            // L'église au milieu, dès le bourg : une nef à pignon et un clocher à flèche.
            if (taille >= 1) {
                c.Maison(new Vector2(0.3f, 0f), 3f, 1.6f, 1.6f, 1.1f, 20f, pierre, toits);
                c.Boite(new Vector3(-1.7f, HAUTEUR_DU_SOCLE_KM, 0f), 1.15f, 3.4f + 0.5f * taille, 1.15f, 20f, pierre); c.Pyramide(new Vector3(-1.7f, HAUTEUR_DU_SOCLE_KM + 3.4f + 0.5f * taille, 0f), 1.4f, 2f, 20f, 4, toits);
            }
            // Les maisons en spirale autour, chacune tournée à sa façon ; aucune sur l'église.
            for (int k = 0; k < maisons; k++) {
                float r = dedans * Mathf.Sqrt((k + 1f) / maisons), angle = k * 2.39996f + taille; var ici = new Vector2(r * Mathf.Cos(angle), r * Mathf.Sin(angle));
                if (taille >= 1 && ici.magnitude < 2.5f) ici = ici.normalized * 2.5f;
                float longue = 1.5f + 0.45f * Hasard(k, taille, 1), haute = 0.8f + 0.4f * Hasard(k, taille, 2);
                c.Maison(ici, longue, 1.1f, haute, 0.8f, 360f * Hasard(k, taille, 3), pierre, toits);
            }
            // Les remparts, dès la ville : un anneau de courtines, et des tours aux angles pour la cité.
            if (taille >= 2) {
                int pans = taille == 2 ? 10 : 12; float tour = rayon - 1f;
                for (int k = 0; k < pans; k++) {
                    float a = 2f * Mathf.PI * k / pans, b = 2f * Mathf.PI * (k + 1) / pans; Vector2 p = new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * tour, q = new Vector2(Mathf.Cos(b), Mathf.Sin(b)) * tour;
                    Vector2 milieu = (p + q) / 2f; c.Boite(new Vector3(milieu.x, HAUTEUR_DU_SOCLE_KM, milieu.y), (q - p).magnitude, 1.2f, 0.45f, -Mathf.Atan2(q.y - p.y, q.x - p.x) * Mathf.Rad2Deg, pierre);
                    if (taille == 3 && k % 3 == 0) { c.Boite(new Vector3(p.x, HAUTEUR_DU_SOCLE_KM, p.y), 1f, 2f, 1f, -a * Mathf.Rad2Deg, pierre); c.Pyramide(new Vector3(p.x, HAUTEUR_DU_SOCLE_KM + 2f, p.y), 1.2f, 1f, -a * Mathf.Rad2Deg, 4, toits); }
                }
            }
            return c.Finir("Bourg de taille " + taille);
        }

        // Une armée, sur un socle au dessus teinté : sa bannière à l'étoffe teintée, qui la domine, et un carré de piquiers
        // quand elle marche, ou trois tentes quand elle assiège.
        public static Mesh Armee(bool auSiege, Color bord, Color acier, Color toile) {
            var c = new Chantier(); c.Socle(RAYON_DE_L_ARMEE_KM, null, bord);
            // La hampe, au nord du socle, et l'étoffe qui flotte vers l'est, face au sud d'où la caméra regarde.
            var pied = new Vector3(-2.2f, HAUTEUR_DU_SOCLE_KM, 2.2f);
            c.Boite(pied, 0.3f, 7.2f, 0.3f, 0f, bord); c.Boite(pied + new Vector3(2.25f, 4.4f, 0f), 4.2f, 2.6f, 0.16f, 0f, null);
            if (auSiege) {
                foreach (var (x, z, cote) in new[] { (1f, -0.4f, 3f), (-1.9f, -1.6f, 2.4f), (2.2f, -2.4f, 2.1f) }) {
                    c.Pyramide(new Vector3(x, HAUTEUR_DU_SOCLE_KM, z), cote, cote * 0.8f, 30f * x, 6, toile);
                    c.Boite(new Vector3(x, HAUTEUR_DU_SOCLE_KM + cote * 0.8f, z), 0.14f, 0.6f, 0.14f, 0f, bord);
                }
            } else {
                // Trois rangs de quatre piquiers, la pique sur l'épaule droite.
                for (int rang = 0; rang < 3; rang++)
                    for (int file = 0; file < 4; file++) {
                        var homme = new Vector3(-1.65f + file * 1.1f, HAUTEUR_DU_SOCLE_KM, 0.6f - rang * 1.1f);
                        c.Boite(homme, 0.7f, 1.5f, 0.55f, 0f, acier); c.Boite(homme + new Vector3(0f, 1.5f, 0f), 0.45f, 0.45f, 0.45f, 0f, toile);
                        c.Boite(homme + new Vector3(0.42f, 0.25f, 0f), 0.1f, 3.6f, 0.1f, 0f, bord);
                    }
            }
            return c.Finir(auSiege ? "Armée au siège" : "Armée en marche");
        }

        // Un nombre de 0 à 1 tiré de trois entiers, toujours le même pour les mêmes.
        private static float Hasard(int a, int b, int c) {
            uint h = unchecked((uint)a * 0x9E3779B1u ^ (uint)b * 0x85EBCA77u ^ (uint)c * 0xC2B2AE3Du);
            h ^= h >> 15; h = unchecked(h * 0x2C1B3C6Du); h ^= h >> 12; h = unchecked(h * 0x297A2D39u); h ^= h >> 15;
            return (h & 0xFFFFFF) / (float)0x1000000;
        }

        // Le chantier d'un maillage à facettes : chaque face a ses sommets et sa normale, tournée vers le dehors du solide.
        // Une couleur absente dit une part teintée : son sommet est blanc, d'alpha 1 ; toute autre couleur a l'alpha 0.
        private sealed class Chantier {
            private readonly List<Vector3> sommets = new List<Vector3>(), normales = new List<Vector3>();
            private readonly List<Color32> couleurs = new List<Color32>(); private readonly List<int> triangles = new List<int>();

            // Une face plane de trois sommets ou plus, donnés dans l'ordre de son tour ; `coeur` est un point du dedans du solide.
            private void Face(Color? couleur, Vector3 coeur, params Vector3[] tour) {
                Vector3 normale = Vector3.Cross(tour[1] - tour[0], tour[2] - tour[0]).normalized, centre = Vector3.zero; foreach (Vector3 p in tour) centre += p; centre /= tour.Length;
                // Le tour se lit dans le sens où sa normale sort du solide : Unity voit alors la face de dehors.
                if (Vector3.Dot(normale, centre - coeur) < 0f) { Array.Reverse(tour); normale = -normale; }
                int premier = sommets.Count; Color32 c = couleur.HasValue ? (Color32)couleur.Value : new Color32(255, 255, 255, 255); c.a = couleur.HasValue ? (byte)0 : (byte)255;
                foreach (Vector3 p in tour) { sommets.Add(p); normales.Add(normale); couleurs.Add(c); }
                for (int k = 1; k + 1 < tour.Length; k++) { triangles.Add(premier); triangles.Add(premier + k); triangles.Add(premier + k + 1); }
            }

            private static Vector3 Tourner(Vector3 p, float cap) { float a = cap * Mathf.Deg2Rad, c = Mathf.Cos(a), s = Mathf.Sin(a); return new Vector3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c); }

            // Une boîte posée sur `base`, longue de `lx`, haute de `h`, profonde de `lz`, tournée de `cap` degrés autour de la verticale.
            public void Boite(Vector3 @base, float lx, float h, float lz, float cap, Color? couleur) {
                Vector3 P(float x, float y, float z) => @base + Tourner(new Vector3(x * lx / 2f, y * h, z * lz / 2f), cap);
                Vector3 coeur = @base + Vector3.up * (h / 2f);
                Face(couleur, coeur, P(-1, 1, -1), P(1, 1, -1), P(1, 1, 1), P(-1, 1, 1));
                Face(couleur, coeur, P(-1, 0, -1), P(1, 0, -1), P(1, 1, -1), P(-1, 1, -1)); Face(couleur, coeur, P(-1, 0, 1), P(1, 0, 1), P(1, 1, 1), P(-1, 1, 1));
                Face(couleur, coeur, P(-1, 0, -1), P(-1, 0, 1), P(-1, 1, 1), P(-1, 1, -1)); Face(couleur, coeur, P(1, 0, -1), P(1, 0, 1), P(1, 1, 1), P(1, 1, -1));
            }

            // Une maison : ses murs, et un toit à deux pans, le faîte dans sa longueur.
            public void Maison(Vector2 ici, float lx, float lz, float murs, float toit, float cap, Color pierre, Color? toits) {
                var @base = new Vector3(ici.x, HAUTEUR_DU_SOCLE_KM, ici.y); Boite(@base, lx, murs, lz, cap, pierre);
                Vector3 P(float x, float y, float z) => @base + Tourner(new Vector3(x * lx / 2f, murs + y * toit, z * lz / 2f), cap);
                Vector3 coeur = @base + Vector3.up * (murs + toit / 3f); const float DEBORD = 1.12f;
                Face(toits, coeur, P(-DEBORD, 0, -DEBORD), P(DEBORD, 0, -DEBORD), P(DEBORD, 1, 0), P(-DEBORD, 1, 0)); Face(toits, coeur, P(-DEBORD, 0, DEBORD), P(DEBORD, 0, DEBORD), P(DEBORD, 1, 0), P(-DEBORD, 1, 0));
                Face(pierre, coeur, P(-1, 0, -1), P(-1, 0, 1), P(-1, 1, 0)); Face(pierre, coeur, P(1, 0, -1), P(1, 0, 1), P(1, 1, 0));
            }

            // Une pyramide à `pans` côtés posée sur `base` : une flèche, un toit de tour, une tente.
            public void Pyramide(Vector3 @base, float cote, float h, float cap, int pans, Color? couleur) {
                Vector3 sommet = @base + Vector3.up * h, coeur = @base + Vector3.up * (h / 4f); float rayon = cote / (2f * Mathf.Cos(Mathf.PI / pans));
                for (int k = 0; k < pans; k++) {
                    float a = 2f * Mathf.PI * (k + 0.5f) / pans, b = 2f * Mathf.PI * (k + 1.5f) / pans;
                    Face(couleur, coeur, @base + Tourner(new Vector3(rayon * Mathf.Cos(a), 0f, rayon * Mathf.Sin(a)), cap), @base + Tourner(new Vector3(rayon * Mathf.Cos(b), 0f, rayon * Mathf.Sin(b)), cap), sommet);
                }
            }

            // Le socle : un disque bas à vingt pans, son dessus d'une couleur et son bord d'une autre.
            public void Socle(float rayon, Color? dessus, Color bord) {
                const int PANS = 20; var tour = new Vector3[PANS]; Vector3 coeur = Vector3.up * (HAUTEUR_DU_SOCLE_KM / 2f);
                for (int k = 0; k < PANS; k++) { float a = 2f * Mathf.PI * k / PANS; tour[k] = new Vector3(rayon * Mathf.Cos(a), HAUTEUR_DU_SOCLE_KM, rayon * Mathf.Sin(a)); }
                Face(dessus, coeur, (Vector3[])tour.Clone());
                // Le bord descend sous le pied du socle : sur une pente, il ne laisse pas de jour.
                for (int k = 0; k < PANS; k++) { Vector3 p = tour[k], q = tour[(k + 1) % PANS], bas = Vector3.down * (HAUTEUR_DU_SOCLE_KM + rayon * 0.35f); Face(bord, coeur, p, q, q + bas, p + bas); }
            }

            public Mesh Finir(string nom) {
                var maillage = new Mesh { name = nom };
                maillage.SetVertices(sommets); maillage.SetNormals(normales); maillage.SetColors(couleurs); maillage.SetTriangles(triangles, 0); maillage.RecalculateBounds();
                return maillage;
            }
        }
    }
}
