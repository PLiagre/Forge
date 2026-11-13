using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Matières de présentation déterministes, sans donnée ni aléa du monde.
    public static class MatieresCabinet
    {
        static Sprite papier, cuir, commande, cire, feuillet, sceau;
        public static Sprite Papier => papier != null ? papier : papier = Fabriquer(false, false);
        public static Sprite Cuir => cuir != null ? cuir : cuir = Fabriquer(true, false);
        public static Sprite Commande => commande != null ? commande : commande = Fabriquer(true, true);
        static Sprite Fabriquer(bool sombre, bool bouton, int filet = 0)
        {
            const int taille = 128;
            var texture = new Texture2D(taille, taille, TextureFormat.RGBA32, false);
            texture.name = sombre ? "Cuir et laiton" : "Papier de chiffon";
            var pixels = new Color[taille * taille];
            Color fond = sombre ? Color.white : SocleInterface.Couleur("papier");
            for (int y = 0; y < taille; y++)
                for (int x = 0; x < taille; x++)
                {
                    int bord = Mathf.Min(x, y, taille - 1 - x, taille - 1 - y);
                    float grain = ((x * 73 + y * 151 + x * y * 3) % 31 - 15) / 3000f;
                    float lumiere = .018f * y / taille + grain;
                    Color c = fond + new Color(lumiere, lumiere, lumiere, 0);
                    if (sombre) c = new Color(.86f + lumiere, .86f + lumiere, .86f + lumiere, 1);
                    if (filet > 0) { if (bord < filet) c = SocleInterface.Couleur("cuivre"); } // le filet de l'infobulle, dans le sprite
                    else if (bord < 2) c = sombre ? new Color(.32f, .30f, .25f) : SocleInterface.Couleur("fond");
                    else if (bord == 3) c = sombre ? new Color(.76f, .68f, .51f) : SocleInterface.Couleur("or");
                    else if (bord < 8 && !bouton) c *= .94f;
                    c.a = 1; pixels[y * taille + x] = c;
                }
            texture.SetPixels(pixels); texture.Apply(false, filet == 0);
            return Sprite.Create(texture, new Rect(0, 0, taille, taille), new Vector2(.5f, .5f), 100, 0,
                SpriteMeshType.FullRect, new Vector4(12, 12, 12, 12));
        }
        // Lot #849 : le papier de chiffon bordé d'un filet de cuivre, épais comme le trait du survol.
        public static Sprite FeuilletDInfobulle => feuillet != null ? feuillet : feuillet = Fabriquer(false, false, EtatsDuCabinet.De(EtatDuCabinet.Survol).Epaisseur);
        public static Sprite Pierre => Matiere("pierre");
        public static Sprite BoisBrule => Matiere("bois-brule");
        public static Sprite Metal => Matiere("metal");
        public static Sprite SceauDeCire => sceau != null ? sceau : sceau = FabriquerSceau();

        const int Taille = 128;
        static readonly Dictionary<string, Sprite> matieres = new Dictionary<string, Sprite>();
        // Le papier et le sang sont des aplats : pas de sprite.
        public static Sprite Matiere(string nom)
        {
            if (Array.IndexOf(Nommees, nom) < 0) return null;
            if (matieres.TryGetValue(nom, out var sprite) && sprite != null) return sprite;
            var texture = new Texture2D(Taille, Taille, TextureFormat.RGBA32, false) { name = nom, wrapMode = TextureWrapMode.Repeat };
            texture.SetPixels32(Pixels(nom)); texture.Apply(false, false);
            return matieres[nom] = Sprite.Create(texture, new Rect(0, 0, Taille, Taille), new Vector2(.5f, .5f), 100, 0, SpriteMeshType.FullRect);
        }

        static readonly string[] Nommees = { "pierre", "bois-brule", "metal" };
        static uint Hache(int x, int y, uint sel)
        {
            unchecked { uint h = (uint)x * 374761393u + (uint)y * 668265263u + sel * 2246822519u; h = (h ^ (h >> 13)) * 1274126177u; return h ^ (h >> 16); }
        }
        static int Bruit(int x, int y, uint sel, int amplitude) => (int)(Hache(x, y, sel) % (uint)(2 * amplitude + 1)) - amplitude;

        // Le calcul est entier et pur : le hachage de x et y, jamais le hasard, l'heure ni la graine du monde. Chaque canal, recentré sur son jeton.
        public static Color32[] Pixels(string matiere)
        {
            if (Array.IndexOf(Nommees, matiere) < 0) throw new ArgumentException("matière inconnue : " + matiere, nameof(matiere));
            var d = new int[3][]; for (int k = 0; k < 3; k++) d[k] = new int[Taille * Taille];
            for (int y = 0; y < Taille; y++)
                for (int x = 0; x < Taille; x++)
                {
                    int v, vert, bleu;
                    if (matiere == "pierre") // des blocs de 64 × 32, un joint de 2 px, un grain
                    {
                        int rang = y / 32, bx = (x + rang % 2 * 32) % Taille;
                        v = y % 32 < 2 || bx % 64 < 2 ? -7 : Bruit(bx / 64 + 2 * rang, 0, 1, 3) + Bruit(x, y, 2, 2); vert = bleu = v;
                    }
                    else if (matiere == "bois-brule") // des fibres horizontales, chaudes
                    {
                        v = Bruit(0, y, 3, 3) + Bruit(x / 24, y, 4, 2) + Bruit(x, y, 5, 1); vert = v * 3 / 4; bleu = v / 2;
                    }
                    else // un brossé fin, et une patine qui verdit par plaques
                    {
                        int patine = Bruit(x / 16, y / 16, 8, 4); v = Bruit(0, y, 6, 2) + Bruit(x / 3, y, 7, 1);
                        vert = v + patine; bleu = v + patine / 2; v -= patine;
                    }
                    d[0][y * Taille + x] = v; d[1][y * Taille + x] = vert; d[2][y * Taille + x] = bleu;
                }
            Color32 jeton = SocleInterface.Couleur(matiere); var pixels = new Color32[Taille * Taille]; int[] moyenne = new int[3];
            for (int k = 0; k < 3; k++) { long somme = 0; foreach (int v in d[k]) somme += v; moyenne[k] = (int)(somme / d[k].Length); }
            byte Borne(int base_, int k, int i) => (byte)Mathf.Clamp(base_ + d[k][i] - moyenne[k], 0, 255);
            for (int i = 0; i < pixels.Length; i++) pixels[i] = new Color32(Borne(jeton.r, 0, i), Borne(jeton.g, 1, i), Borne(jeton.b, 2, i), 255);
            return pixels;
        }

        public static void Habiller(Image image, bool sombre = false, bool bouton = false, bool infobulle = false)
        {
            image.sprite = infobulle ? FeuilletDInfobulle : bouton ? Commande : sombre ? Cuir : Papier;
            image.type = Image.Type.Sliced;
            image.color = sombre && !bouton ? SocleInterface.Couleur("fond") : Color.white;
        }
        public static void Engagement(Button bouton)
        {
            var couleurs = bouton.colors;
            couleurs.normalColor = SocleInterface.Couleur("alerte");
            couleurs.highlightedColor = new Color(.65f, .27f, .21f);
            couleurs.pressedColor = new Color(.30f, .09f, .07f);
            bouton.colors = couleurs;
            var sceau = new GameObject("Sceau de l’engagement", typeof(RectTransform), typeof(Image));
            var rect = sceau.GetComponent<RectTransform>(); rect.SetParent(bouton.transform, false);
            rect.anchorMin = rect.anchorMax = new Vector2(0, .5f);
            rect.anchoredPosition = new Vector2(20, 0); rect.sizeDelta = new Vector2(28, 28);
            var image = sceau.GetComponent<Image>(); image.raycastTarget = false;
            image.sprite = Cire();
        }
        // Le sceau du registre : de la cire `sang`, un anneau clair et une croix creusée qui se compensent.
        static Sprite FabriquerSceau()
        {
            const int taille = 64;
            var texture = new Texture2D(taille, taille, TextureFormat.RGBA32, false) { name = "Cire du registre" };
            Color sang = SocleInterface.Couleur("sang");
            for (int y = 0; y < taille; y++)
                for (int x = 0; x < taille; x++)
                {
                    float dx = x - 31.5f, dy = y - 31.5f, r = Mathf.Sqrt(dx * dx + dy * dy), bord = 29 + Mathf.Sin(Mathf.Atan2(dy, dx) * 11) * 1.2f;
                    Color c = sang;
                    if (r > 22 && r < 25) c = Color.Lerp(sang, Color.white, .12f);
                    if ((Mathf.Abs(dx) < 2 && Mathf.Abs(dy) < 13) || (Mathf.Abs(dy) < 2 && Mathf.Abs(dx) < 9)) c *= .7f;
                    c.a = Mathf.Clamp01(bord - r); texture.SetPixel(x, y, c);
                }
            texture.Apply(false, false);
            return Sprite.Create(texture, new Rect(0, 0, taille, taille), new Vector2(.5f, .5f));
        }
        static Sprite Cire()
        {
            if (cire != null) return cire;
            const int taille = 64;
            var texture = new Texture2D(taille, taille, TextureFormat.RGBA32, false);
            for (int y = 0; y < taille; y++)
                for (int x = 0; x < taille; x++)
                {
                    float dx = x - 31.5f, dy = y - 31.5f;
                    float r = Mathf.Sqrt(dx * dx + dy * dy);
                    float bord = 29 + Mathf.Sin(Mathf.Atan2(dy, dx) * 11) * 1.2f;
                    var c = new Color(.55f + dy / 400f, .19f + dy / 900f, .13f);
                    if (r > 22 && r < 25) c = new Color(.75f, .40f, .25f);
                    if ((Mathf.Abs(dx) < 2 && Mathf.Abs(dy) < 13) || (Mathf.Abs(dy) < 2 && Mathf.Abs(dx) < 9)) c *= .65f;
                    c.a = Mathf.Clamp01(bord - r); texture.SetPixel(x, y, c);
                }
            texture.Apply(false, true);
            return cire = Sprite.Create(texture, new Rect(0, 0, taille, taille), new Vector2(.5f, .5f));
        }
    }
}
