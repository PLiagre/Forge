using System;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace Forge.Pont
{
    // Lot #780 — la garniture d'un étal montre le stock d'une seule marchandise du bourg, d'après les lectures #778 : une vue, jamais
    // une règle du monde. La garniture, enfant de l'étal pivoté à sa base, a la forme du plein ; seule sa hauteur suit
    // `min(1, stock_kg / reference_kg)`. La référence est un réglage de représentation, ni capacité ni besoin. Zéro : garniture masquée,
    // le comptoir reste. La faim n'est pas lue : elle ne remplit ni ne vide l'étal. Un refus masque la garniture et nomme sa cause.
    [ExecuteAlways]
    public sealed class EtalDuBourg : MonoBehaviour
    {
        private Transform garniture; private Vector3 plein; private long cellId; private bool propre; // propre : enfant de l'étal à la configuration.
        public Transform Garniture => garniture; public Vector3 Plein => plein;
        public string Marchandise { get; private set; } public double ReferenceKg { get; private set; }
        public string Cause { get; private set; } = "aucune lecture"; // null : lectures concordantes, garniture appliquée, zéro compris.
        public double Rapport { get; private set; } = -1; // -1 : non calculé ; 0 est une mesure.

        // L'échelle du plein est prise ici, une fois par garniture : reconfigurer la même ne la relit pas déjà réduite.
        // L'ancienne garniture propre est masquée et rendue à son plein ; une garniture étrangère est mémorisée pour être refusée, jamais touchée.
        public void Configurer(long cellId, string marchandise, double referenceKg, Transform garniture)
        {
            Masquer("aucune lecture");
            if (garniture != this.garniture) { if (propre && this.garniture != null) this.garniture.localScale = plein;
                propre = garniture != null && garniture != transform && garniture.IsChildOf(transform); plein = garniture != null ? garniture.localScale : Vector3.zero; }
            this.cellId = cellId; Marchandise = marchandise; ReferenceKg = referenceKg; this.garniture = garniture; Masquer("aucune lecture");
        }

        public bool Appliquer(Lecture<BourgLu> bourg, LecturePlan plan)
        {
            string refus = Refus(bourg, plan, out double kg);
            if (refus != null) { Masquer(refus); return false; }
            double rapport = Math.Min(1.0, kg / ReferenceKg); // En double, converti seulement pour l'échelle.
            garniture.localScale = new Vector3(plein.x, (float)(plein.y * rapport), plein.z);
            Cause = null; Rapport = rapport; Montrer(rapport > 0); return true;
        }

        private string Refus(Lecture<BourgLu> bourg, LecturePlan plan, out double kg)
        {
            kg = double.NaN; if (!isActiveAndEnabled) return "composant désactivé";
            if (string.IsNullOrWhiteSpace(Marchandise)) return "marchandise vide : un étal désigne sa clé";
            if (!(ReferenceKg > 0) || double.IsInfinity(ReferenceKg)) return "référence invalide : " + ReferenceKg.ToString(CultureInfo.InvariantCulture) + " kg (positive et finie attendue)";
            if (!propre || garniture == null || !garniture.IsChildOf(transform)) return "garniture absente ou hors de l'étal";
            if (!garniture.GetComponentsInChildren<MeshRenderer>(true).Any(r => r.TryGetComponent(out MeshFilter f) && f.sharedMesh != null))
                return "garniture sans géométrie : un MeshRenderer et son maillage attendus";
            if (plan == null || !plan.Presente) return "plan absent : " + (plan?.Absence ?? "non fourni");
            if (bourg == null || !bourg.Presente) return "bourg absent : " + (bourg?.Absence ?? "non fourni");
            PlanLu p = plan.Plan; BourgLu b = bourg.Donnees;
            if (p.CellId != cellId || b.CellId != cellId) return "cellule différente de " + T(cellId) + " : plan " + T(p.CellId) + ", bourg " + T(b.CellId);
            if (b.Rang != 0) return "rang 0 attendu : bourg " + T(b.Rang);
            if (b.Tick != p.Tick || b.TickLocal != p.Tick) return "tick différent du plan " + T(p.Tick) + " : bourg " + T(b.Tick) + " (local " + T(b.TickLocal) + ")";
            // La clé exacte, sans alias ni marchandise de remplacement ; aucun repli sur la cellule, les champs ou le grenier.
            if (!b.Stocks.TryGetValue(Marchandise, out kg)) return "« " + Marchandise + " » absente du bourg " + T(cellId);
            if (!(kg >= 0) || double.IsInfinity(kg)) return "stock invalide de « " + Marchandise + " » : " + kg.ToString(CultureInfo.InvariantCulture);
            return null;
        }

        // Rien d'ancien ne reste affiché ; seuls les rendus de la garniture changent, jamais le comptoir, l'auvent ni un matériau.
        private void Masquer(string cause) { Cause = cause; Rapport = -1; Montrer(false); }
        private void Montrer(bool visible)
        {
            if (!propre || garniture == null) return; // Ni l'étal entier ni la garniture d'un autre ne sont jamais masqués.
            foreach (var r in garniture.GetComponentsInChildren<Renderer>(true)) r.enabled = visible;
        }
        private void OnDisable() => Masquer("composant désactivé"); private void OnDestroy() => Masquer("composant détruit");
        private static string T(long n) => n.ToString(CultureInfo.InvariantCulture);
    }
}
