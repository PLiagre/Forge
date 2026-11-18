using UnityEngine;

namespace Forge.Pont {
    // Le geste du joueur qui parcourt sa carte, image après image, sous une caméra inclinée. Au bouton enfoncé, le
    // point du sol sous la souris est saisi, relief compris ; tant que le bouton est tenu, la vue se déplace pour que
    // ce point reste sous la souris, où qu'elle aille. La molette rapproche ou éloigne du point du sol sous la souris,
    // qui reste sous elle. Le point se lit par le rayon de l'écran jusqu'au sol dessiné (`CarteDessinee.SolSous`), à
    // la pose que la caméra a reçue à l'image d'avant ; hors du sol, il se lit au niveau de la mer.
    // Ne lit aucune souris : celui qui l'appelle dit où elle est et ce qu'elle fait.
    public sealed class ParcoursDeVue {
        private Vector3? saisi; // le point du sol saisi, en local dans la carte
        public bool Glisse => saisi.HasValue;
        public Vector3? Saisi => saisi;

        // Une image du geste : la souris est en `ecran` (pixels) ; `appui` dit que le bouton vient d'être enfoncé sur
        // la carte, `tenu` qu'il l'est encore ; `crans` de molette, positifs pour s'approcher.
        public void Pas(CarteDessinee carte, Vector2 ecran, bool appui, bool tenu, float crans) {
            VueDeCarte vue = carte != null ? carte.Vue : null; Camera camera = carte != null ? carte.camera : null;
            if (vue == null || camera == null) { saisi = null; return; }
            Vector2 ancre = camera.ScreenToViewportPoint(ecran);
            if (!tenu) saisi = null;
            else if (appui) saisi = Sous(carte, vue, ecran, ancre);
            else if (saisi is Vector3 point) vue.Amener(new Vector2(point.x, point.z), ancre, point.y);
            if (crans == 0f) return;
            Vector3 ici = saisi ?? Sous(carte, vue, ecran, ancre);
            vue.Zoomer(crans, ancre, ici.y);
        }

        // Le point du sol sous la souris, en local ; au niveau de la mer quand le rayon ne trouve pas le sol.
        private static Vector3 Sous(CarteDessinee carte, VueDeCarte vue, Vector2 ecran, Vector2 ancre) {
            if (carte.SolSous(ecran) is Vector3 monde) return carte.transform.InverseTransformPoint(monde);
            Vector2 plat = vue.PointSous(ancre); return new Vector3(plat.x, 0f, plat.y);
        }
    }
}
