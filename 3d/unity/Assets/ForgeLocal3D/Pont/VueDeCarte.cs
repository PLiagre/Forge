using UnityEngine;

namespace Forge.Pont {
    // Ce que montre la caméra de la carte, et ses bornes. La caméra regarde vers le nord, en perspective, penchée sur
    // la carte : de loin elle la voit presque d'en haut, et plus le joueur s'approche, plus elle s'incline. Elle vise
    // `Centre`, un point du niveau de la mer, et montre autour de lui `Demi` km de haut en bas de l'écran ; c'est ce
    // rectangle visé, large de `DemiLargeur`, que les bornes tiennent dans la carte servie : sur un axe où il est
    // plus large que la carte, il se centre sur elle ; sur l'autre, il reste dedans. Le zoom va de toute la carte
    // (`Echelle` 1) à `DEMI_MIN_KM` de demi-hauteur. Il est relatif à toute la carte : quand la fenêtre change de
    // forme, toute la carte reste toute la carte.
    // Le glisser et la molette tiennent un point du sol sous la souris : ce point se lit par le rayon de l'écran,
    // au niveau où le sol se trouve sous elle, et la vue se déplace pour l'y ramener. Rien ici ne touche une caméra
    // avant `Poser` : les rayons se calculent de la pose seule.
    // Coordonnées locales de la carte, en km : x vers l'est, y vers le haut, z vers le nord ; `Centre` porte (x, z).
    public sealed class VueDeCarte {
        public const float DEMI_MIN_KM = 50f; // une centaine de km de haut : une cellule et ses voisines
        public const float MARGE = 1.03f; // celle du cadre de toute la carte
        // Ce que la perspective resserre du bord du sud, le plus près de la caméra : une carte cadrée sur sa largeur
        // l'est d'autant plus large, pour que ses deux coins du sud tiennent dans la vue.
        public const float RESSERRE_AU_SUD = 1.08f;
        public const float PAS_DE_ZOOM = 0.85f; // par cran de molette, comme la caméra de la ville
        // Le champ de la caméra, de haut en bas ; et son inclinaison sous l'horizon, sur toute la carte puis au plus près.
        public const float CHAMP = 30f, INCLINAISON_LOIN = 68f, INCLINAISON_PRES = 48f;
        // Les plans de coupe, en parts de la distance à la visée : le sol reste entre les deux à toute inclinaison.
        public const float PLAN_PROCHE = 0.05f, PLAN_LOINTAIN = 4f;
        private static readonly float DEMI_CHAMP = Mathf.Tan(CHAMP * Mathf.Deg2Rad / 2f);
        private readonly Bounds boite;

        public VueDeCarte(Bounds boite, float aspect) {
            this.boite = boite; Centre = new Vector2(boite.center.x, boite.center.z); Changer(aspect);
        }

        public float Aspect { get; private set; } = 1f;
        public Vector2 Centre { get; private set; }
        public float Echelle { get; private set; } = 1f;
        public float DemiMax => Mathf.Max(boite.extents.z, boite.extents.x * RESSERRE_AU_SUD / Aspect) * MARGE;
        public float EchelleMin => Mathf.Min(1f, DEMI_MIN_KM / DemiMax);
        public float Demi => DemiMax * Echelle; // la demi-hauteur montrée autour du point visé
        public float DemiLargeur => Demi * Aspect;
        // De combien la caméra regarde sous l'horizon, en degrés : d'autant moins que la vue est proche.
        public float Inclinaison => Mathf.Lerp(INCLINAISON_LOIN, INCLINAISON_PRES, EchelleMin < 1f ? Mathf.Log(Echelle) / Mathf.Log(EchelleMin) : 0f);
        // La distance de la caméra au point visé : celle d'où `Demi` remplit la moitié du champ.
        public float Distance => Demi / DEMI_CHAMP;
        // Vers où la caméra regarde, son haut, et où elle se tient, en local dans la carte.
        public Vector3 Regard { get { float a = Inclinaison * Mathf.Deg2Rad; return new Vector3(0f, -Mathf.Sin(a), Mathf.Cos(a)); } }
        public Vector3 Haut { get { float a = Inclinaison * Mathf.Deg2Rad; return new Vector3(0f, Mathf.Cos(a), Mathf.Sin(a)); } }
        public Vector3 Position => new Vector3(Centre.x, 0f, Centre.y) - Regard * Distance;

        // La fenêtre a changé de forme : même échelle, bornes recalculées.
        public void Changer(float aspect) { Aspect = aspect > 0 ? aspect : 1f; Borner(); }

        // Le point du sol (x, z) sous `ancre` (0 à 1 dans la fenêtre, depuis le bas à gauche), là où le sol est à cette hauteur.
        public Vector2 PointSous(Vector2 ancre, float hauteur = 0f) {
            Vector3 d = Regard + Vector3.right * (DEMI_CHAMP * Aspect * (2f * ancre.x - 1f)) + Haut * (DEMI_CHAMP * (2f * ancre.y - 1f)), p = Position;
            // Sous l'horizon, le rayon descend toujours : la caméra penche de plus que la moitié de son champ.
            float t = (hauteur - p.y) / Mathf.Min(d.y, -1e-6f);
            return new Vector2(p.x + d.x * t, p.z + d.z * t);
        }

        // Ramène sous `ancre` ce point du sol, de cette hauteur, sauf là où une borne l'en empêche.
        public void Amener(Vector2 point, Vector2 ancre, float hauteur = 0f) { Centre += point - PointSous(ancre, hauteur); Borner(); }

        // La carte suit la souris : le point du sol qui était sous `de` vient sous `a`.
        public void Glisser(Vector2 de, Vector2 a, float hauteur = 0f) => Amener(PointSous(de, hauteur), a, hauteur);

        // Le même geste mesuré au point visé, à plat : `pixels` à l'écran, sur un écran de `hauteurPx` pixels de haut.
        public void Glisser(Vector2 pixels, float hauteurPx) {
            if (hauteurPx <= 0) return;
            Centre -= pixels * (2 * Demi / hauteurPx); Borner();
        }

        // `crans` positifs : on s'approche. Le point du sol sous `ancre`, de cette hauteur, reste sous elle, sauf là où
        // une borne l'en empêche.
        public void Zoomer(float crans, Vector2 ancre, float hauteur = 0f) {
            Vector2 point = PointSous(ancre, hauteur);
            Echelle = Mathf.Clamp(Echelle * Mathf.Pow(PAS_DE_ZOOM, crans), EchelleMin, 1f);
            Amener(point, ancre, hauteur);
        }

        public void Centrer(Vector2 centre, float demi) { Centre = centre; Echelle = DemiMax > 0f ? demi / DemiMax : 1f; Borner(); } // `demi` demandée, puis les bornes

        // Pose la caméra sur la vue : en perspective, à sa place et sous son inclinaison, ses plans de coupe réglés sur sa distance.
        public void Poser(Camera camera, Transform carte) {
            camera.orthographic = false; camera.fieldOfView = CHAMP;
            camera.nearClipPlane = Mathf.Max(0.01f, Distance * PLAN_PROCHE); camera.farClipPlane = Distance * PLAN_LOINTAIN;
            camera.transform.SetPositionAndRotation(carte.TransformPoint(Position), carte.rotation * Quaternion.LookRotation(Regard, Haut));
        }

        private void Borner() {
            Echelle = Mathf.Clamp(Echelle, EchelleMin, 1f);
            Centre = new Vector2(Axe(Centre.x, boite.min.x, boite.max.x, DemiLargeur), Axe(Centre.y, boite.min.z, boite.max.z, Demi));
        }

        private static float Axe(float centre, float min, float max, float demi) =>
            2 * demi >= max - min ? (min + max) / 2 : Mathf.Clamp(centre, min + demi, max - demi);
    }
}
