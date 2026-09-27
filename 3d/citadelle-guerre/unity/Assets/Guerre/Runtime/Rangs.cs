using System.Collections.Generic;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;

namespace Guerre
{
    public static class Rangs
    {
        // Les hommes reprennent un numéro dans l'ordre où ils se tiennent : les plus avancés
        // forment le premier rang, de gauche à droite. Personne n'a à traverser le régiment
        // pour rejoindre sa place quand le front change ou que des morts ouvrent des vides.
        public static void Reclasser(EntityManager em, List<Entity> regiments)
        {
            em.CompleteAllTrackedJobs();
            var q = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var sold = q.ToComponentDataArray<Soldat>(Allocator.Temp);
            using var pos = q.ToComponentDataArray<LocalTransform>(Allocator.Temp);
            var parRegiment = new Dictionary<Entity, List<int>>();
            foreach (var e in regiments) if (em.Exists(e)) parRegiment[e] = new List<int>();
            for (int i = 0; i < ents.Length; i++)
                if (parRegiment.TryGetValue(sold[i].Regiment, out var l)) l.Add(i);

            foreach (var (e, hommes) in parRegiment)
            {
                var r = em.GetComponentData<Regiment>(e);
                // L'effectif suit les vivants : c'est lui qui dessine la formation.
                r.Effectif = hommes.Count;
                em.SetComponentData(e, r);
                if (hommes.Count == 0) continue;
                float2 droite = new float2(r.Front.y, -r.Front.x);
                hommes.Sort((a, b) => math.dot(pos[b].Position.xz - r.Position, r.Front).CompareTo(math.dot(pos[a].Position.xz - r.Position, r.Front)));
                int files = math.max(1, math.min(r.Files, hommes.Count));
                for (int debut = 0; debut < hommes.Count; debut += files)
                {
                    int n = math.min(files, hommes.Count - debut);
                    var rang = hommes.GetRange(debut, n);
                    rang.Sort((a, b) => math.dot(pos[a].Position.xz - r.Position, droite).CompareTo(math.dot(pos[b].Position.xz - r.Position, droite)));
                    for (int k = 0; k < n; k++)
                    {
                        var s = sold[rang[k]];
                        s.Numero = debut + k;
                        em.SetComponentData(ents[rang[k]], s);
                    }
                }
            }
        }
    }
}
