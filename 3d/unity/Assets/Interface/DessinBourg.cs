using System;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Forge.Interface
{
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class DessinBourg : MaskableGraphic, IPointerClickHandler
    {
        PlanBourg plan;
        Vector2[] brouillon = Array.Empty<Vector2>();
        public Action<Vector2> Pointer;
        public void Esquisser(Vector2[] points) { brouillon = points; SetVerticesDirty(); }
        public void OnPointerClick(PointerEventData evenement)
        {
            if (plan == null || evenement.button != PointerEventData.InputButton.Left || Pointer == null) return;
            if (RectTransformUtility.ScreenPointToLocalPointInRectangle(rectTransform, evenement.position, evenement.pressEventCamera, out var point))
                Pointer((point - rectTransform.rect.center) / PixelsParMetre + (plan.Minimum + plan.Maximum) / 2);
        }
        public float PixelsParMetre => plan == null ? 0 : Mathf.Min((rectTransform.rect.width - 32) / (plan.Maximum.x - plan.Minimum.x),
            (rectTransform.rect.height - 32) / (plan.Maximum.y - plan.Minimum.y));
        public void Afficher(PlanBourg valeur) { plan = valeur; SetVerticesDirty(); }
        protected override void OnPopulateMesh(VertexHelper dessin)
        {
            dessin.Clear();
            if (plan == null) return;
            float echelle = PixelsParMetre;
            Vector2 centre = (plan.Minimum + plan.Maximum) / 2;
            var esquisse = new PlanBourg.Trace { Points = brouillon, Nature = "chantier", Fermee = false, Largeur = 2 / echelle };
            foreach (var trace in plan.Traces.Concat(new[] { esquisse }))
            {
                string jeton = trace.Nature == "chantier" ? "alerte" : trace.Nature == "rue" ? "accent"
                    : trace.Nature == "place" || trace.Nature == "parcelle" ? "or" : "encre";
                Color teinte = SocleInterface.Couleur(jeton);
                int segments = trace.Points.Length - (trace.Fermee ? 0 : 1);
                for (int i = 0; i < segments; i++)
                {
                    Vector2 a = (trace.Points[i] - centre) * echelle + rectTransform.rect.center;
                    Vector2 b = (trace.Points[(i + 1) % trace.Points.Length] - centre) * echelle + rectTransform.rect.center;
                    Vector2 delta = b - a;
                    if (delta.sqrMagnitude == 0) continue;
                    float largeur = trace.Fermee ? 2 : Mathf.Max(1, trace.Largeur * echelle);
                    Vector2 normale = new Vector2(-delta.y, delta.x).normalized * largeur / 2;
                    int debut = dessin.currentVertCount;
                    foreach (var point in new[] { a - normale, a + normale, b + normale, b - normale })
                        dessin.AddVert(point, teinte, Vector2.zero);
                    dessin.AddTriangle(debut, debut + 1, debut + 2);
                    dessin.AddTriangle(debut, debut + 2, debut + 3);
                }
            }
        }
    }
}
