using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Rendering;
using Unity.Transforms;

namespace Guerre
{
    // L'ancre de chaque régiment avance vers sa cible et tourne sans à-coup.
    // Tant que le joueur n'a pas pris la main, le scénario de démonstration
    // fait marcher les deux armées l'une vers l'autre, puis les ramène.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemeRegiments : ISystem
    {
        const float PivotMax = 0.35f;       // rad/s : un bloc de 250 hommes ne pivote pas sur place
        const float Halte = 8f;             // secondes d'arrêt sur chaque ligne

        public void OnCreate(ref SystemState state) => state.RequireForUpdate<Regiment>();

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            float dt = SystemAPI.Time.DeltaTime;
            foreach (var reg in SystemAPI.Query<RefRW<Regiment>>())
            {
                ref var r = ref reg.ValueRW;
                float2 vers = r.Cible - r.Position;
                float dist = math.length(vers);
                if (dist > 0.3f)
                {
                    float2 dir = vers / dist;
                    // Loin de la cible, on marche face à elle ; près, on se remet face au front voulu.
                    r.Front = Tourner(r.Front, dist > 6f ? dir : r.FrontCible, PivotMax * dt);
                    // On n'avance vraiment qu'une fois tourné vers la marche : le pivot passe d'abord.
                    float aligne = math.saturate(math.dot(r.Front, dir));
                    r.Position += dir * math.min(dist, r.VitesseMarche * dt * math.max(aligne, 0.25f));
                }
                else
                {
                    r.Front = Tourner(r.Front, r.FrontCible, PivotMax * dt);
                    if (r.Ordonne == 0)
                    {
                        r.Attente += dt;
                        if (r.Attente > Halte)
                        {
                            r.Attente = 0;
                            r.Etape = 1 - r.Etape;
                            r.Cible = r.Etape == 1 ? r.Avant : r.Base;
                        }
                    }
                }
            }
        }

        static float2 Tourner(float2 de, float2 vers, float maxAngle)
        {
            float a = math.atan2(de.y, de.x), b = math.atan2(vers.y, vers.x);
            float d = b - a;
            d = math.atan2(math.sin(d), math.cos(d));
            a += math.clamp(d, -maxAngle, maxAngle);
            return new float2(math.cos(a), math.sin(a));
        }
    }

    // Chaque soldat cherche sa place, garde son élan et s'écarte de ses voisins.
    // La formation qui se déforme au pivot ou dans un goulet n'est écrite nulle part :
    // elle naît de ces trois tendances.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemeRegiments))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemePilotage : ISystem
    {
        public const float Cellule = 1.2f;
        NativeParallelMultiHashMap<int, float2> grille;
        ComponentLookup<Regiment> regiments;
        EntityQuery soldats;

        public void OnCreate(ref SystemState state)
        {
            grille = new NativeParallelMultiHashMap<int, float2>(16384, Allocator.Persistent);
            regiments = state.GetComponentLookup<Regiment>(true);
            soldats = SystemAPI.QueryBuilder().WithAll<Soldat, LocalTransform>().Build();
            state.RequireForUpdate<Relief>();
            state.RequireForUpdate(soldats);
        }

        public void OnDestroy(ref SystemState state)
        {
            if (grille.IsCreated) grille.Dispose();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            int n = soldats.CalculateEntityCount();
            if (grille.Capacity < n)
            {
                state.Dependency.Complete();
                grille.Capacity = n * 2;
            }
            regiments.Update(ref state);
            var relief = SystemAPI.GetSingleton<Relief>().Blob;
            // Un pas de temps trop long (chargement, fenêtre déplacée) ferait traverser les voisins.
            float dt = math.min(SystemAPI.Time.DeltaTime, 1f / 20f);

            var dep = new ViderGrille { Grille = grille }.Schedule(state.Dependency);
            dep = new RemplirGrille { Grille = grille.AsParallelWriter() }.ScheduleParallel(dep);
            dep = new Piloter { Grille = grille, Regiments = regiments, Relief = relief, Dt = dt }.ScheduleParallel(dep);
            state.Dependency = dep;
        }

        public static int Cle(int2 c) => (c.x * 73856093) ^ (c.y * 19349663);

        [BurstCompile]
        struct ViderGrille : IJob
        {
            public NativeParallelMultiHashMap<int, float2> Grille;
            public void Execute() => Grille.Clear();
        }

        [BurstCompile]
        partial struct RemplirGrille : IJobEntity
        {
            public NativeParallelMultiHashMap<int, float2>.ParallelWriter Grille;
            void Execute(in Soldat s, in LocalTransform t)
            {
                float2 p = t.Position.xz;
                Grille.Add(Cle((int2)math.floor(p / Cellule)), p);
            }
        }

        [BurstCompile]
        partial struct Piloter : IJobEntity
        {
            [ReadOnly] public NativeParallelMultiHashMap<int, float2> Grille;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            public float Dt;

            const float Rayon = 0.85f;        // distance à laquelle deux hommes se gênent
            const float Repousse = 2.2f;      // m/s d'écart quand ils se touchent
            const float Acceleration = 3.5f;  // m/s² : un homme en armure ne vire pas net
            const float VitesseMax = 2.6f;    // m/s : le pas de course pour rattraper sa place

            void Execute(ref Soldat s, ref LocalTransform t)
            {
                var r = Regiments[s.Regiment];
                float2 front = r.Front, droite = new float2(front.y, -front.x);
                float2 place = r.Position + droite * s.Place.x + front * s.Place.y;
                float2 pos = t.Position.xz;

                float2 vers = place - pos;
                float dist = math.length(vers);
                float vMax = VitesseMax * s.Allure;
                // Arrivée douce : on ralentit en approchant de sa place.
                float2 voulu = dist > 0.02f ? vers / dist * math.min(vMax, dist * 1.4f) : float2.zero;

                float2 ecart = float2.zero;
                int2 c = (int2)math.floor(pos / Cellule);
                for (int dz = -1; dz <= 1; dz++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out float2 q, out var it)) continue;
                    do
                    {
                        float2 d = pos - q;
                        float l2 = math.lengthsq(d);
                        if (l2 > 1e-8f && l2 < Rayon * Rayon)
                        {
                            float l = math.sqrt(l2);
                            ecart += d / l * (1f - l / Rayon);
                        }
                    } while (Grille.TryGetNextValue(out q, ref it));
                }
                voulu += ecart * Repousse;

                float2 dv = voulu - s.Vitesse;
                float ldv = math.length(dv), maxDv = Acceleration * Dt;
                if (ldv > maxDv) dv *= maxDv / ldv;
                s.Vitesse += dv;
                float v = math.length(s.Vitesse);
                if (v > vMax * 1.2f) { s.Vitesse *= vMax * 1.2f / v; v = vMax * 1.2f; }
                pos += s.Vitesse * Dt;

                // Le pas : une légère élévation à chaque foulée, proportionnelle à l'allure.
                s.Phase += v * Dt * 3.4f;
                float marche = math.saturate(v / 1.2f);
                float y = Sol.Hauteur(ref Relief.Value, pos) + math.abs(math.sin(s.Phase)) * 0.06f * marche;

                float2 regard = v > 0.35f ? math.normalize(s.Vitesse) : front;
                var cible = quaternion.LookRotationSafe(new float3(regard.x, 0, regard.y), math.up());
                t.Rotation = math.slerp(t.Rotation, cible, math.saturate(Dt * 5f));
                t.Position = new float3(pos.x, y, pos.y);
            }
        }
    }

    // La couleur du camp, éclaircie pour le régiment choisi par le joueur.
    [BurstCompile]
    [UpdateInGroup(typeof(PresentationSystemGroup))]
    public partial struct SystemeCouleurs : ISystem
    {
        ComponentLookup<Regiment> regiments;

        public void OnCreate(ref SystemState state)
        {
            regiments = state.GetComponentLookup<Regiment>(true);
            state.RequireForUpdate<Soldat>();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            regiments.Update(ref state);
            state.Dependency = new Teindre { Regiments = regiments }.ScheduleParallel(state.Dependency);
        }

        [BurstCompile]
        partial struct Teindre : IJobEntity
        {
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            void Execute(in Soldat s, ref URPMaterialPropertyBaseColor c)
            {
                float3 t = s.Teinte;
                if (Regiments[s.Regiment].Selection != 0) t = math.lerp(t, new float3(1f, 0.92f, 0.55f), 0.55f);
                c.Value = new float4(t, 1f);
            }
        }
    }
}
