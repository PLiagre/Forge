using UnityEngine;

namespace Forge.Pont {
    // Ce que montre la caméra de la carte, et ses bornes. La caméra regarde la carte d'en haut, à la verticale, nord en
    // haut de l'écran, en perspective pour que le relief s'y lise. Elle vise `Centre`, un point du niveau de la mer, et
    // montre autour de lui `Demi` km de haut en bas de l'écran, `DemiLargeur` de gauche à droite.
    // Une part de l'écran peut être prise par l'interface : la vue ne connaît que sa partie libre (`Libre`, en parts de
    // la fenêtre, depuis le bas à gauche ; tout l'écran sans `Liberer`). Le point visé est celui du sol sous le milieu
    // de la partie libre (`Vise`), et c'est lui que les bornes tiennent dans la carte servie : de près, il va jusqu'au
    // bord de la carte, et l'écran montre au-delà ce que le terrain y dessine. Au plus loin (`Echelle` 1), toute la carte
    // tient dans la partie libre, et la touche sur l'axe le plus serré. Entre les deux, plus la partie libre approche de la
    // taille de la carte sur un axe, moins le point visé peut s'écarter du milieu de la carte sur cet axe
    // (`DEBORD_TOTAL`) : la carte revient sans saut au milieu de la partie libre quand on recule vers le plus loin. Le
    // zoom va de là à `DEMI_MIN_KM` de demi-hauteur, relatif au plus loin : quand la fenêtre change de forme, le plus loin
    // reste le plus loin ; quand la partie libre change, la vue garde sa demi-hauteur, et seules ses bornes changent.
    // La vue s'ouvre sur la carte qui remplit l'écran sur son axe le plus serré (`DemiPleine`), centrée.
    // Le glisser et la molette tiennent un point du sol sous la souris : ce point se lit par le rayon de l'écran,
    // au niveau où le sol se trouve sous elle, et la vue se déplace pour l'y ramener. Rien ici ne touche une caméra
    // avant `Poser` : les rayons se calculent de la pose seule.
    // Coordonnées locales de la carte, en km : x vers l'est, y vers le haut, z vers le nord ; `Centre` porte (x, z).
    public sealed class VueDeCarte {
        public const float DEMI_MIN_KM = 50f; // une centaine de km de haut : une province et ses lieux
        public const float MARGE = 1.03f; // celle d'un cadrage demandé autour d'un ensemble de lieux
        public const float PAS_DE_ZOOM = 0.85f; // par cran de molette, comme la caméra de la ville
        public const float CHAMP = 30f; // le champ de la caméra, de haut en bas
        // La part de la demi-carte, sur un axe, en deçà de laquelle la demi-partie libre laisse le point visé aller
        // jusqu'au bord de la carte ; au-delà, le débord permis décroît jusqu'à zéro quand la partie libre a la taille
        // de la carte.
        public const float DEBORD_TOTAL = 2f / 3f;
        // Les plans de coupe, en parts de la distance à la visée : le sol et ses sommets restent entre les deux.
        public const float PLAN_PROCHE = 0.05f, PLAN_LOINTAIN = 4f;
        private static readonly float DEMI_CHAMP = Mathf.Tan(CHAMP * Mathf.Deg2Rad / 2f);
        private static readonly Rect TOUT = new Rect(0f, 0f, 1f, 1f);
        private readonly Bounds boite;

        public VueDeCarte(Bounds boite, float aspect) {
            this.boite = boite; Centre = new Vector2(boite.center.x, boite.center.z); Changer(aspect);
        }
        // Tant que rien n'a mené la vue, elle reste celle d'ouverture, quelle que soit la forme que prend la fenêtre.
        private bool aLOuverture = true;

        public float Aspect { get; private set; } = 1f;
        public Rect Libre { get; private set; } = TOUT;
        public Vector2 Centre { get; private set; }
        public float Echelle { get; private set; } = 1f;
        // Au plus loin : toute la carte dans la partie libre, sur ses deux axes.
        public float DemiMax => Mathf.Max(boite.extents.z / Libre.height, boite.extents.x / (Aspect * Libre.width));
        // La carte qui remplit l'écran entier sur son axe le plus serré : la vue d'ouverture.
        public float DemiPleine => Mathf.Min(boite.extents.z, boite.extents.x / Aspect);
        public float EchelleMin => Mathf.Min(1f, DEMI_MIN_KM / DemiMax);
        public float Demi => DemiMax * Echelle; // la demi-hauteur montrée autour du point visé
        public float DemiLargeur => Demi * Aspect;
        // Le point du niveau de la mer sous le milieu de la partie libre.
        public Vector2 Vise => PointSous(Libre.center);
        // La distance de la caméra au point visé : celle d'où `Demi` remplit la moitié du champ.
        public float Distance => Demi / DEMI_CHAMP;
        // Vers où la caméra regarde (le bas), son haut (le nord), et où elle se tient, en local dans la carte.
        public Vector3 Regard => Vector3.down;
        public Vector3 Haut => Vector3.forward;
        public Vector3 Position => new Vector3(Centre.x, 0f, Centre.y) - Regard * Distance;

        // La fenêtre a changé de forme : même échelle, bornes recalculées ; à l'ouverture, la carte remplit de nouveau l'écran.
        public void Changer(float aspect) {
            Aspect = aspect > 0 ? aspect : 1f;
            if (aLOuverture && DemiMax > 0f) Echelle = DemiPleine / DemiMax;
            Borner();
        }

        // La partie de l'écran que l'interface laisse à la carte, en parts de la fenêtre : la vue garde sa demi-hauteur
        // et son centre, seules ses bornes changent. Une partie vide, ou qui sort de la fenêtre, est refusée. Vrai si la
        // partie libre a changé.
        public bool Liberer(Rect libre) {
            if (!(libre.width > 0f && libre.height > 0f && libre.xMin >= 0f && libre.yMin >= 0f && libre.xMax <= 1f && libre.yMax <= 1f))
                throw new System.ArgumentException("partie libre hors de la fenêtre, ou vide : " + libre);
            if (libre == Libre) return false;
            float demi = Demi; Libre = libre; Echelle = demi / DemiMax; Borner(); return true;
        }

        // Le point du sol (x, z) sous `ancre` (0 à 1 dans la fenêtre, depuis le bas à gauche), là où le sol est à cette hauteur.
        public Vector2 PointSous(Vector2 ancre, float hauteur = 0f) {
            Vector3 d = Regard + Vector3.right * (DEMI_CHAMP * Aspect * (2f * ancre.x - 1f)) + Haut * (DEMI_CHAMP * (2f * ancre.y - 1f)), p = Position;
            // Le rayon descend toujours : la caméra regarde à la verticale.
            float t = (hauteur - p.y) / Mathf.Min(d.y, -1e-6f);
            return new Vector2(p.x + d.x * t, p.z + d.z * t);
        }

        // Ramène sous `ancre` ce point du sol, de cette hauteur, sauf là où une borne l'en empêche.
        public void Amener(Vector2 point, Vector2 ancre, float hauteur = 0f) { aLOuverture = false; Centre += point - PointSous(ancre, hauteur); Borner(); }

        // La carte suit la souris : le point du sol qui était sous `de` vient sous `a`.
        public void Glisser(Vector2 de, Vector2 a, float hauteur = 0f) => Amener(PointSous(de, hauteur), a, hauteur);

        // Le même geste mesuré au niveau de la mer : `pixels` à l'écran, sur un écran de `hauteurPx` pixels de haut.
        public void Glisser(Vector2 pixels, float hauteurPx) {
            if (hauteurPx <= 0) return;
            aLOuverture = false; Centre -= pixels * (2 * Demi / hauteurPx); Borner();
        }

        // `crans` positifs : on s'approche. Le point du sol sous `ancre`, de cette hauteur, reste sous elle, sauf là où
        // une borne l'en empêche.
        public void Zoomer(float crans, Vector2 ancre, float hauteur = 0f) {
            Vector2 point = PointSous(ancre, hauteur); aLOuverture = false;
            Echelle = Mathf.Clamp(Echelle * Mathf.Pow(PAS_DE_ZOOM, crans), EchelleMin, 1f);
            Amener(point, ancre, hauteur);
        }

        public void Centrer(Vector2 centre, float demi) { aLOuverture = false; Centre = centre; Echelle = DemiMax > 0f ? demi / DemiMax : 1f; Borner(); } // `demi` demandée, puis les bornes

        // Pose la caméra sur la vue : en perspective, à l'aplomb du point visé, ses plans de coupe réglés sur sa distance.
        public void Poser(Camera camera, Transform carte) {
            camera.orthographic = false; camera.fieldOfView = CHAMP;
            camera.nearClipPlane = Mathf.Max(0.01f, Distance * PLAN_PROCHE); camera.farClipPlane = Distance * PLAN_LOINTAIN;
            camera.transform.SetPositionAndRotation(carte.TransformPoint(Position), carte.rotation * Quaternion.LookRotation(Regard, Haut));
        }

        // Le point visé, sur chaque axe, dans ce que `Axe` permet ; le centre se tient à son écart fixe du point visé, relu
        // de la borne et non du point d'avant, qu'un glissé démesuré a pu porter là où un flottant perd ses kilomètres.
        // Un axe que la borne ne touche pas garde son centre au bit près.
        private void Borner() {
            Echelle = Mathf.Clamp(Echelle, EchelleMin, 1f);
            Vector2 ecart = new Vector2((2f * Libre.center.x - 1f) * DemiLargeur, (2f * Libre.center.y - 1f) * Demi), vise = Centre + ecart;
            float x = Axe(vise.x, boite.min.x, boite.max.x, DemiLargeur * Libre.width), z = Axe(vise.y, boite.min.z, boite.max.z, Demi * Libre.height);
            Centre = new Vector2(x == vise.x ? Centre.x : x - ecart.x, z == vise.y ? Centre.y : z - ecart.y);
        }

        // Sur un axe de la carte, de `min` à `max`, où peut se tenir le point visé quand la demi-partie libre y couvre
        // `libre` km. La partie libre peut déborder de la carte d'au plus `debord` de chaque côté : toute sa moitié de
        // près, rien quand elle a la taille de la carte. Plus grande que la carte, elle est centrée sur elle.
        private static float Axe(float vise, float min, float max, float libre) {
            float demiCarte = (max - min) / 2f;
            float debord = Mathf.Clamp(Mathf.Min(libre, (demiCarte - libre) * DEBORD_TOTAL / (1f - DEBORD_TOTAL)), 0f, libre);
            float bas = min + libre - debord, haut = max - libre + debord;
            return bas > haut ? (min + max) / 2f : Mathf.Clamp(vise, bas, haut);
        }
    }
}
