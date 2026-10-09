using UnityEngine;

namespace Forge.Pont {
    // Lot #524 : ce que montre la caméra de la carte, vue de dessus, nord en haut, et ses bornes. Le joueur glisse et zoome ;
    // la vue ne sort jamais de la carte servie : sur un axe où elle est plus large que la carte, elle se centre sur elle ;
    // sur l'autre, elle reste dedans. Le zoom va de toute la carte (`Echelle` 1, le cadre de #548) à `DEMI_MIN_KM` de
    // demi-hauteur. Il est relatif à toute la carte : quand la fenêtre change de forme, toute la carte reste toute la carte.
    // Coordonnées locales de la carte, en km : x vers l'est, z vers le nord ; `Centre` porte (x, z).
    public sealed class VueDeCarte {
        public const float DEMI_MIN_KM = 50f; // une centaine de km de haut : une cellule et ses voisines
        public const float MARGE = 1.03f; // celle du cadre de toute la carte (#548)
        public const float PAS_DE_ZOOM = 0.85f; // par cran de molette, comme la caméra de la ville
        private readonly Bounds boite;

        public VueDeCarte(Bounds boite, float aspect) {
            this.boite = boite; Centre = new Vector2(boite.center.x, boite.center.z); Changer(aspect);
        }

        public float Aspect { get; private set; } = 1f;
        public Vector2 Centre { get; private set; }
        public float Echelle { get; private set; } = 1f;
        public float DemiMax => Mathf.Max(boite.extents.z, boite.extents.x / Aspect) * MARGE;
        public float EchelleMin => Mathf.Min(1f, DEMI_MIN_KM / DemiMax);
        public float Demi => DemiMax * Echelle; // la demi-hauteur montrée : l'`orthographicSize`
        public float DemiLargeur => Demi * Aspect;

        // La fenêtre a changé de forme : même échelle, bornes recalculées.
        public void Changer(float aspect) { Aspect = aspect > 0 ? aspect : 1f; Borner(); }

        // La carte suit la souris : `pixels` à l'écran, sur un écran de `hauteurPx` pixels de haut.
        public void Glisser(Vector2 pixels, float hauteurPx) {
            if (hauteurPx <= 0) return;
            Centre -= pixels * (2 * Demi / hauteurPx); Borner();
        }

        // `crans` positifs : on s'approche. Le point sous `ancre` (0 à 1 dans la fenêtre, depuis le bas à gauche) reste
        // sous elle, sauf là où une borne l'en empêche.
        public void Zoomer(float crans, Vector2 ancre) {
            Vector2 point = Centre + Decalage(ancre);
            Echelle = Mathf.Clamp(Echelle * Mathf.Pow(PAS_DE_ZOOM, crans), EchelleMin, 1f);
            Centre = point - Decalage(ancre); Borner();
        }

        // Le point de la carte (x, z) sous `ancre`.
        public Vector2 PointSous(Vector2 ancre) => Centre + Decalage(ancre);

        public void Poser(Camera camera, Transform carte, float hauteur) {
            camera.transform.SetPositionAndRotation(carte.TransformPoint(new Vector3(Centre.x, hauteur, Centre.y)), Quaternion.Euler(90, 0, 0));
            camera.orthographicSize = Demi;
        }

        private Vector2 Decalage(Vector2 ancre) => new Vector2((ancre.x - .5f) * 2 * DemiLargeur, (ancre.y - .5f) * 2 * Demi);

        private void Borner() {
            Echelle = Mathf.Clamp(Echelle, EchelleMin, 1f);
            Centre = new Vector2(Axe(Centre.x, boite.min.x, boite.max.x, DemiLargeur), Axe(Centre.y, boite.min.z, boite.max.z, Demi));
        }

        private static float Axe(float centre, float min, float max, float demi) =>
            2 * demi >= max - min ? (min + max) / 2 : Mathf.Clamp(centre, min + demi, max - demi);
    }
}
