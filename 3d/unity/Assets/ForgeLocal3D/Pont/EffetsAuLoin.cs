using System;
using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont
{
    // Lot #961 — le niveau de détail des effets de la capitale dense : une vue, jamais une règle du monde ; n'agit que si `OptimisationsDeLaVille.Actives`.
    // `EffetsDeMaison` décide si une maison fume et s'éclaire ; ce composant décide seulement si on le montre : il coupe une lampe voulue
    // (intensité > 0) sans toucher à son intensité, et met en pause une fumée sans l'arrêter. Il rend tout ce qu'il a pris en se désactivant.
    public sealed class EffetsAuLoin : MonoBehaviour
    {
        public const int PLAFOND_DES_LAMPES = 32;
        public const float DISTANCE_DES_FUMEES_M = 60f;
        private readonly List<EffetsDeMaison> effets = new List<EffetsDeMaison>();
        private readonly Dictionary<ParticleSystem, ParticleSystemCullingMode> notes = new Dictionary<ParticleSystem, ParticleSystemCullingMode>();
        private readonly HashSet<ParticleSystem> retenues = new HashSet<ParticleSystem>();
        private Camera oeil;
        public bool Actif { get; private set; } public int Effets => effets.Count; public Camera Camera => oeil;

        // Parmi les lampes voulues, les `plafond` plus proches de `oeil` (carrés comparés ; à égalité, l'indice le plus petit d'abord).
        public static bool[] LampesAllumees(Vector3 oeil, IReadOnlyList<Vector3> positions, IReadOnlyList<bool> voulues, int plafond)
        {
            Verifier(oeil, positions); if (voulues == null) throw new ArgumentNullException(nameof(voulues));
            if (voulues.Count != positions.Count) throw new ArgumentException(positions.Count + " positions pour " + voulues.Count + " lampes voulues", nameof(voulues));
            if (plafond < 0) throw new ArgumentOutOfRangeException(nameof(plafond), plafond, "plafond négatif");
            var rangs = new List<int>(); var carres = new float[positions.Count];
            for (int i = 0; i < positions.Count; i++) if (voulues[i]) { carres[i] = (positions[i] - oeil).sqrMagnitude; rangs.Add(i); }
            rangs.Sort((a, b) => carres[a] != carres[b] ? carres[a].CompareTo(carres[b]) : a.CompareTo(b));
            var allumees = new bool[positions.Count]; for (int k = 0; k < rangs.Count && k < plafond; k++) allumees[rangs[k]] = true;
            return allumees;
        }
        // Vrai si la fumée est strictement plus loin que `distanceM` de `oeil`, en trois dimensions.
        public static bool[] FumeesEnPause(Vector3 oeil, IReadOnlyList<Vector3> positions, float distanceM)
        {
            Verifier(oeil, positions);
            if (!(distanceM > 0f) || float.IsInfinity(distanceM)) throw new ArgumentOutOfRangeException(nameof(distanceM), distanceM, "distance finie et positive attendue");
            var pause = new bool[positions.Count]; float limite = distanceM * distanceM;
            for (int i = 0; i < positions.Count; i++) pause[i] = (positions[i] - oeil).sqrMagnitude > limite;
            return pause;
        }
        private static void Verifier(Vector3 oeil, IReadOnlyList<Vector3> positions)
        {
            if (positions == null) throw new ArgumentNullException(nameof(positions));
            if (!Fini(oeil)) throw new ArgumentException("œil non fini : " + oeil, nameof(oeil));
            for (int i = 0; i < positions.Count; i++) if (!Fini(positions[i])) throw new ArgumentException("position non finie au rang " + i + " : " + positions[i], nameof(positions));
        }
        private static bool Fini(Vector3 v) => !float.IsNaN(v.x) && !float.IsInfinity(v.x) && !float.IsNaN(v.y) && !float.IsInfinity(v.y) && !float.IsNaN(v.z) && !float.IsInfinity(v.z);

        public void Configurer(Camera camera, IReadOnlyList<EffetsDeMaison> effets)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));
            if (effets == null) throw new ArgumentNullException(nameof(effets));
            for (int i = 0; i < effets.Count; i++) if (effets[i] == null) throw new ArgumentNullException(nameof(effets), "effet nul au rang " + i);
            Rendre(); oeil = camera; this.effets.Clear(); this.effets.AddRange(effets);
            Actif = OptimisationsDeLaVille.Actives; Prendre();
        }
        // Les fumées hors de l'image cessent d'être simulées : `Automatic` vaut `Pause` pour une fumée en boucle.
        private void Prendre()
        {
            if (!Actif) return;
            foreach (var e in effets)
            {
                var f = e != null ? e.Fumee : null; if (f == null || notes.ContainsKey(f)) continue;
                var m = f.main; notes.Add(f, m.cullingMode); m.cullingMode = ParticleSystemCullingMode.Automatic;
            }
        }
        private void LateUpdate() => Regler();
        public void Regler()
        {
            if (!Actif || oeil == null || effets.Count == 0) return;
            Vector3 o = oeil.transform.position; int n = effets.Count;
            var lampes = new Vector3[n]; var voulues = new bool[n]; var fumees = new Vector3[n];
            for (int i = 0; i < n; i++)
            {
                var e = effets[i]; var l = e != null ? e.Lampe : null; var f = e != null ? e.Fumee : null;
                if (l != null) { lampes[i] = l.transform.position; voulues[i] = l.intensity > 0f; }
                fumees[i] = f != null ? f.transform.position : o;
            }
            bool[] allumees = LampesAllumees(o, lampes, voulues, PLAFOND_DES_LAMPES), pause = FumeesEnPause(o, fumees, DISTANCE_DES_FUMEES_M);
            for (int i = 0; i < n; i++)
            {
                var e = effets[i]; if (e == null) continue;
                var l = e.Lampe; if (l != null && voulues[i] && l.enabled != allumees[i]) l.enabled = allumees[i];
                var f = e.Fumee; if (f == null) continue;
                if (retenues.Contains(f) && f.isStopped) retenues.Remove(f); // `EffetsDeMaison` l'a éteinte : elle n'est plus à lui.
                if (pause[i]) { if (f.isPlaying) { f.Pause(true); retenues.Add(f); } } // Relancée par `Appliquer`, elle est remise en pause.
                else if (retenues.Remove(f) && f.isPaused) f.Play(true);
            }
        }
        // Rien ne reste éteint par lui : lampes voulues rallumées, fumées retenues relancées, culling d'origine rendu.
        private void Rendre()
        {
            foreach (var e in effets) { var l = e != null ? e.Lampe : null; if (Actif && l != null && l.intensity > 0f) l.enabled = true; }
            foreach (var f in retenues) if (f != null && f.isPaused) f.Play(true);
            foreach (var kv in notes) if (kv.Key != null) { var m = kv.Key.main; m.cullingMode = kv.Value; }
            retenues.Clear(); notes.Clear();
        }
        private void OnEnable() => Prendre(); private void OnDisable() => Rendre(); private void OnDestroy() => Rendre();
    }
}
