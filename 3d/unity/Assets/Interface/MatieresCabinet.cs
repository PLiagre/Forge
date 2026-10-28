using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Matières de présentation déterministes, sans donnée ni aléa du monde.
    public static class MatieresCabinet
    {
        static Sprite papier, cuir, commande, cire;
        public static Sprite Papier => papier != null ? papier : papier = Fabriquer(false, false);
        public static Sprite Cuir => cuir != null ? cuir : cuir = Fabriquer(true, false);
        public static Sprite Commande => commande != null ? commande : commande = Fabriquer(true, true);
        static Sprite Fabriquer(bool sombre, bool bouton)
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
                    if (bord < 2) c = sombre ? new Color(.32f, .30f, .25f) : SocleInterface.Couleur("fond");
                    else if (bord == 3) c = sombre ? new Color(.76f, .68f, .51f) : SocleInterface.Couleur("or");
                    else if (bord < 8 && !bouton) c *= .94f;
                    c.a = 1; pixels[y * taille + x] = c;
                }
            texture.SetPixels(pixels); texture.Apply(false, true);
            return Sprite.Create(texture, new Rect(0, 0, taille, taille), new Vector2(.5f, .5f), 100, 0,
                SpriteMeshType.FullRect, new Vector4(12, 12, 12, 12));
        }
        public static void Habiller(Image image, bool sombre = false, bool bouton = false)
        {
            image.sprite = bouton ? Commande : sombre ? Cuir : Papier;
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
