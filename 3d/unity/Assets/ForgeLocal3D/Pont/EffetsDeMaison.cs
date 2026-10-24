using System.Globalization;
using UnityEngine;

namespace Forge.Pont
{
    // Lot #779 — la fumée et la lampe d'une maison de la capitale, d'après les lectures #778 : une vue, jamais une règle du monde.
    // Habitée : toute case de la base de 1400, une maison bâtie si `Loges > 0` (−1 : inconnue, refusée). La fumée veut en plus la
    // nourriture du bourg présente et > 0 ; la lampe suit le soir de `DesertEnvironment`. Un refus éteint les deux et nomme sa cause.
    [ExecuteAlways]
    public sealed class EffetsDeMaison : MonoBehaviour
    {
        private ParticleSystem fumee; private Light lampe; private float intensite;
        private long cellId, rang, foyer, batiment; private bool deBase;
        public ParticleSystem Fumee => fumee; public Light Lampe => lampe; public bool Habitee { get; private set; }
        public string Cause { get; private set; } = "aucune lecture"; // null : lectures concordantes, effets appliqués.
        public string AbsenceAlimentaire { get; private set; } // null : nourriture servie, zéro compris.

        // Une case de la base, `plan.Base.Maisons[rang]` et son foyer `foyer`, ou un bâtiment de geste : jamais les deux.
        public void PourLaBase(ParticleSystem fumee, Light lampe, long cellId, long rang, long foyer)
        { Initialiser(fumee, lampe, cellId); deBase = true; this.rang = rang; this.foyer = foyer; }
        public void PourLeBatiment(ParticleSystem fumee, Light lampe, long cellId, long identifiant)
        { Initialiser(fumee, lampe, cellId); deBase = false; batiment = identifiant; }
        // Les anciennes références s'éteignent ; l'intensité positive configurée est gardée : le soir s'y mesure, jamais à l'intensité courante.
        private void Initialiser(ParticleSystem f, Light l, long cellule)
        {
            Eteindre("aucune lecture"); if (l != lampe || !(intensite > 0)) intensite = l != null ? l.intensity : 0f;
            fumee = f; lampe = l; cellId = cellule; Eteindre("aucune lecture");
        }
        // `heure` : celle de la présentation (12 à 22), jamais déduite du tick.
        public bool Appliquer(Lecture<BourgLu> bourg, Lecture<OccupationLue> occupation, LecturePlan plan, float heure)
        {
            string refus = Refus(bourg, occupation, plan, heure, out bool habitee);
            if (refus != null) { Eteindre(refus); return false; }
            bool servie = bourg.Donnees.Stocks.TryGetValue("nourriture", out double kg);
            Cause = null; Habitee = habitee; AbsenceAlimentaire = servie ? null : "nourriture absente du bourg " + T(cellId) + " : pas de fumée";
            if (habitee && servie && kg > 0) { if (!fumee.isPlaying) fumee.Play(true); }
            else fumee.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            float soir = habitee ? Mathf.InverseLerp(18.2f, 21f, heure) * intensite : 0f;
            lampe.intensity = soir; lampe.enabled = soir > 0f; return true;
        }
        private string Refus(Lecture<BourgLu> bourg, Lecture<OccupationLue> occupation, LecturePlan plan, float heure, out bool habitee)
        {
            habitee = false; if (!isActiveAndEnabled) return "composant désactivé";
            if (fumee == null || lampe == null || lampe.type != LightType.Point || !(intensite > 0) || !fumee.transform.IsChildOf(transform) || !lampe.transform.IsChildOf(transform))
                return "références manquantes : une fumée et une lampe ponctuelle d'intensité positive, enfants de la maison";
            if (!(heure >= 12f && heure <= 22f)) return "heure invalide : " + heure.ToString(CultureInfo.InvariantCulture) + " (12 à 22 attendu)";
            if (plan == null || !plan.Presente) return "plan absent : " + (plan?.Absence ?? "non fourni");
            if (bourg == null || !bourg.Presente) return "bourg absent : " + (bourg?.Absence ?? "non fourni");
            if (occupation == null || !occupation.Presente) return "occupation absente : " + (occupation?.Absence ?? "non fournie");
            PlanLu p = plan.Plan; BourgLu b = bourg.Donnees; OccupationLue o = occupation.Donnees;
            if (p.CellId != cellId || b.CellId != cellId || o.CellId != cellId)
                return "cellule différente de " + T(cellId) + " : plan " + T(p.CellId) + ", bourg " + T(b.CellId) + ", occupation " + T(o.CellId);
            if (b.Rang != 0 || o.Rang != 0) return "rang 0 attendu : bourg " + T(b.Rang) + ", occupation " + T(o.Rang);
            if (b.Tick != p.Tick || b.TickLocal != p.Tick || o.Tick != p.Tick)
                return "tick différent du plan " + T(p.Tick) + " : bourg " + T(b.Tick) + " (local " + T(b.TickLocal) + "), occupation " + T(o.Tick);
            if (deBase)
            {
                if (p.Base == null || rang < 0 || rang >= p.Base.Maisons.Count) return "case de base introuvable : rang " + T(rang);
                long foyers = p.Base.Maisons[(int)rang].Foyers;
                if (rang >= o.Base.Count || o.Base[(int)rang].Rang != rang || o.Base[(int)rang].Foyers != foyers) return "compte de base différent au rang " + T(rang);
                if (foyer < 0 || foyer >= foyers) return "indice de foyer " + T(foyer) + " hors de 0.." + T(foyers - 1);
                habitee = true; return null; // Toute la base est habitée, logement calculé ou non.
            }
            BatimentDuPlan m = null; foreach (var x in p.Batiments) if (x.Identifiant == batiment) m = x;
            if (m == null) return "bâtiment " + T(batiment) + " introuvable au plan";
            if (m.Nature != "maison" || m.EnChantier) return "bâtiment " + T(batiment) + " : pas une maison achevée (" + m.Nature + (m.EnChantier ? ", chantier)" : ")");
            foreach (var (id, _, loges) in o.Batiments)
                if (id == batiment) { habitee = loges > 0; return loges < 0 ? "occupation inconnue du bâtiment " + T(batiment) : null; }
            return "bâtiment " + T(batiment) + " absent de l'occupation";
        }
        // Rien d'ancien ne reste affiché : l'émission s'arrête, les particules s'effacent, la lampe s'éteint.
        private void Eteindre(string cause)
        {
            Cause = cause; Habitee = false; AbsenceAlimentaire = null;
            if (fumee != null) fumee.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            if (lampe != null) { lampe.intensity = 0f; lampe.enabled = false; }
        }
        private void OnDisable() => Eteindre("composant désactivé"); private void OnDestroy() => Eteindre("composant détruit");
        private static string T(long n) => n.ToString(CultureInfo.InvariantCulture);
    }
}
