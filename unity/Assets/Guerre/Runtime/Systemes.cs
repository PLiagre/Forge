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
        const float Halte = 8f;             // secondes d'arrêt sur chaque ligne
        const float VitesseAile = 1.6f;     // m/s : l'allure que les hommes de l'aile tiennent en pivot
        const float MarcheLongue = 30f;     // au-delà, le régiment se tourne vers sa marche ; en deçà, il garde son front

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
                // Le régiment attend ses hommes : si ceux-ci sont loin de leur place
                // (gênés, bousculés, essoufflés), l'ordre ralentit avec eux.
                float cohesion = 1f - math.smoothstep(1.5f, 5f, r.Ecart);
                // Un front large pivote lentement : ses ailes doivent courir.
                float pivot = math.min(0.5f, VitesseAile / math.max(r.Largeur * 0.5f, 1f)) * math.max(cohesion, 0.15f) * dt;
                if (dist > 0.3f)
                {
                    float2 dir = vers / dist;
                    bool longue = dist > MarcheLongue;
                    r.Front = Tourner(r.Front, longue ? dir : r.FrontCible, pivot);
                    // En marche longue, on n'avance vraiment qu'une fois tourné vers elle.
                    // En marche courte, les hommes se décalent ou reculent sans tourner le dos.
                    float allure = longue ? math.max(math.saturate(math.dot(r.Front, dir)), 0.25f) : 0.7f;
                    r.Position += dir * math.min(dist, r.VitesseMarche * dt * allure * cohesion);
                }
                else
                {
                    r.Front = Tourner(r.Front, r.FrontCible, pivot);
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
        NativeParallelMultiHashMap<int, Voisin> grille;
        ComponentLookup<Regiment> regiments;
        EntityQuery soldats;

        public void OnCreate(ref SystemState state)
        {
            grille = new NativeParallelMultiHashMap<int, Voisin>(16384, Allocator.Persistent);
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

            byte corps = SystemAPI.TryGetSingleton<ReglagesSimulation>(out var reglages) ? reglages.Corps : (byte)1;

            var dep = new ViderGrille { Grille = grille }.Schedule(state.Dependency);
            dep = new RemplirGrille { Grille = grille.AsParallelWriter() }.ScheduleParallel(dep);
            dep = new Piloter { Grille = grille, Regiments = regiments, Relief = relief, Dt = dt, Corps = corps }.ScheduleParallel(dep);
            state.Dependency = dep;
        }

        // Un homme campé (arrêté, à sa place) a ses appuis au sol : il cède moins
        // qu'un homme en marche quand un autre régiment le bouscule, et s'efface
        // devant un camarade qui rejoint sa place.
        public static float Appui(in Soldat s)
        {
            float campe = math.saturate(1f - math.length(s.Vitesse) / 0.8f) * (1f - math.smoothstep(0.5f, 1.5f, s.Ecart));
            return 1f + 3f * campe;
        }

        public static int Cle(int2 c) => (c.x * 73856093) ^ (c.y * 19349663);

        public struct Voisin { public float2 P; public int Id, Regiment; public float Appui; }

        [BurstCompile]
        struct ViderGrille : IJob
        {
            public NativeParallelMultiHashMap<int, Voisin> Grille;
            public void Execute() => Grille.Clear();
        }

        [BurstCompile]
        partial struct RemplirGrille : IJobEntity
        {
            public NativeParallelMultiHashMap<int, Voisin>.ParallelWriter Grille;
            void Execute(Entity e, in Soldat s, in LocalTransform t)
            {
                float2 p = t.Position.xz;
                Grille.Add(Cle((int2)math.floor(p / Cellule)), new Voisin { P = p, Id = e.Index, Regiment = s.Regiment.Index, Appui = Appui(s) });
            }
        }

        [BurstCompile]
        partial struct Piloter : IJobEntity
        {
            [ReadOnly] public NativeParallelMultiHashMap<int, Voisin> Grille;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            public float Dt;
            public byte Corps;

            const float Rayon = 0.85f;        // distance à laquelle deux hommes se gênent
            const float Repousse = 2.2f;      // m/s d'écart quand ils se touchent
            const float Diametre = 0.8f;      // épaules, bouclier, coudes : deux hommes ne se recouvrent pas
            const float Acceleration = 3.5f;  // m/s² : un homme en armure ne vire pas net
            const float VitesseMax = 2.6f;    // m/s : le pas de course pour rattraper sa place

            void Execute(Entity e, ref Soldat s, ref LocalTransform t)
            {
                var r = Regiments[s.Regiment];
                float2 front = r.Front;
                float2 place = Formation.VersMonde(Formation.Place(r, s.Numero) + s.Decalage, r.Position, front);
                float2 pos = t.Position.xz;

                float2 vers = place - pos;
                float dist = math.length(vers);
                float vMax = VitesseMax * s.Allure;
                // Arrivée douce : on ralentit en approchant de sa place. Bousculé de
                // quelques dizaines de centimètres, on la reprend franchement.
                float gain = math.lerp(3f, 1.4f, math.saturate(dist - 0.5f));
                float2 voulu = dist > 0.02f ? vers / dist * math.min(vMax, dist * gain) : float2.zero;
                float appui = Appui(s);

                int2 c = (int2)math.floor(pos / Cellule);
                if (Corps != 0)
                {
                    // L'espace personnel face aux autres régiments : on s'écarte avant de se toucher.
                    // Entre camarades, c'est la place dans les rangs qui fixe l'intervalle.
                    float2 ecart = float2.zero;
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.Id == e.Index || q.Regiment == s.Regiment.Index) continue;
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d);
                            if (l2 > 1e-8f && l2 < Rayon * Rayon)
                            {
                                float l = math.sqrt(l2);
                                ecart += d / l * (1f - l / Rayon);
                            }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                    voulu += ecart * Repousse;
                }

                float2 dv = voulu - s.Vitesse;
                float ldv = math.length(dv), maxDv = Acceleration * Dt;
                if (ldv > maxDv) dv *= maxDv / ldv;
                s.Vitesse += dv;
                float v = math.length(s.Vitesse);
                if (v > vMax * 1.2f) { s.Vitesse *= vMax * 1.2f / v; v = vMax * 1.2f; }
                float2 avant = pos;
                pos += s.Vitesse * Dt;

                if (Corps != 0)
                {
                    // Les corps : si un voisin est à moins d'un diamètre, chacun cède une part
                    // du recouvrement selon ses appuis. Aucun homme ne traverse un autre, il le pousse.
                    c = (int2)math.floor(pos / Cellule);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.Id == e.Index) continue;
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d);
                            if (l2 < Diametre * Diametre)
                            {
                                float l = math.sqrt(l2);
                                float2 n = l > 1e-4f ? d / l : math.normalizesafe(avant - q.P, new float2(1, 0));
                                // Face à un autre régiment, l'homme campé tient. Entre camarades, c'est
                                // l'inverse : celui qui est à sa place s'efface devant celui qui rejoint la sienne.
                                float part = q.Regiment == s.Regiment.Index ? appui / (appui + q.Appui) : q.Appui / (appui + q.Appui);
                                pos += n * (Diametre - l) * part;
                            }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                    // Ce qu'on a été empêché de faire, on ne l'a pas fait : l'élan suit le mouvement réel.
                    s.Vitesse = math.lerp(s.Vitesse, (pos - avant) / math.max(Dt, 1e-4f), 0.5f);
                    v = math.length(s.Vitesse);
                }
                s.Ecart = math.distance(pos, place);

                // Le pas : une légère élévation à chaque foulée, proportionnelle à l'allure.
                s.Phase += v * Dt * 3.4f;
                float marche = math.saturate(v / 1.2f);
                float y = Sol.Hauteur(ref Relief.Value, pos) + math.abs(math.sin(s.Phase)) * 0.06f * marche;

                // On regarde où l'on va, sauf quand on recule : on garde alors l'ennemi en face.
                float2 dirV = v > 0.35f ? s.Vitesse / v : front;
                float2 regard = math.dot(dirV, front) > -0.2f ? dirV : front;
                var cible = quaternion.LookRotationSafe(new float3(regard.x, 0, regard.y), math.up());
                t.Rotation = math.slerp(t.Rotation, cible, math.saturate(Dt * 5f));
                t.Position = new float3(pos.x, y, pos.y);
            }
        }
    }

    // L'écart moyen des hommes à leur place remonte au régiment : c'est ainsi
    // qu'un ordre attend ceux qu'il commande.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemePilotage))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemeCohesion : ISystem
    {
        NativeArray<float2> sommes;
        ComponentLookup<Regiment> regiments;
        EntityQuery regimentsQuery;

        public void OnCreate(ref SystemState state)
        {
            regiments = state.GetComponentLookup<Regiment>(true);
            regimentsQuery = SystemAPI.QueryBuilder().WithAll<Regiment>().Build();
            state.RequireForUpdate<Soldat>();
        }

        public void OnDestroy(ref SystemState state)
        {
            if (sommes.IsCreated) sommes.Dispose();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            int n = regimentsQuery.CalculateEntityCount();
            if (!sommes.IsCreated || sommes.Length < n)
            {
                state.Dependency.Complete();
                if (sommes.IsCreated) sommes.Dispose();
                sommes = new NativeArray<float2>(math.max(n, 64), Allocator.Persistent);
            }
            regiments.Update(ref state);
            var dep = new Additionner { Sommes = sommes, Regiments = regiments }.Schedule(state.Dependency);
            state.Dependency = new Reporter { Sommes = sommes }.Schedule(dep);
        }

        [BurstCompile]
        partial struct Additionner : IJobEntity
        {
            public NativeArray<float2> Sommes;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            void Execute(in Soldat s)
            {
                int i = Regiments[s.Regiment].Index;
                Sommes[i] += new float2(s.Ecart, 1);
            }
        }

        [BurstCompile]
        partial struct Reporter : IJobEntity
        {
            public NativeArray<float2> Sommes;
            void Execute(ref Regiment r)
            {
                var s = Sommes[r.Index];
                r.Ecart = s.y > 0 ? s.x / s.y : 0;
                Sommes[r.Index] = float2.zero;
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
