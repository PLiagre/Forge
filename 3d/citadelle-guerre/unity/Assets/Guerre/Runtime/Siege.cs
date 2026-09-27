using System.Collections.Generic;
using System.Linq;
using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Transforms;
using UnityEngine;

namespace Guerre
{
    // Une pierre d'un pan de mur appareillé : en place, en train de tomber, ou à terre dans les gravats.
    // Le mur n'a pas de points de vie : il tient tant que ses pierres reposent les unes sur les autres.
    public struct Pierre : IComponentData
    {
        public int Index;
        public float3 V, Tourne;   // vitesse (m/s) et rotation (rad/s) pendant la chute
    }

    // Un boulet de pierre, tiré par une bombarde ou un trébuchet.
    public struct Boulet : IComponentData
    {
        public float3 P, V;
        public float Masse, Rayon, Vie;
        public byte Etat;          // 0 libre, 1 en vol, 2 tombé
    }

    public struct Impact { public int Pierre; public float3 Point, Direction; public float Energie, Quantite; }
    public struct Depot { public float3 P; public float Volume; }

    public static class Maconnerie
    {
        // Ce que tient le mortier d'une pierre : il faut lui communiquer cette énergie pour la déloger.
        public const float Liaison = 150000f;   // J
        // L'énergie d'un choc se répartit sur les pierres voisines, dans toutes les directions.
        public const float Diffusion = 0.8f;    // m
        public const float Densite = 2300f;     // kg/m³
        // Une pierre tient si le tiers de sa longueur au moins repose encore sur les pierres du dessous.
        public const float AppuiMin = 1f / 3f;
    }

    // Les pans de mur, les boulets, les chutes. Les pierres sont levées par Bataille (LeverMurs) ; ce système
    // tient leurs données, fait voler les boulets, applique les chocs, fait tomber ce qui ne repose plus sur
    // rien, et dépose les pierres tombées en gravats dans le relief.
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemePilotage))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial class SystemeMurs : SystemBase
    {
        public NativeArray<float3> Centres, Tailles;
        public NativeArray<quaternion> Orientations;
        public NativeArray<int> Pans, Couches, Assises, DebutAppuis, NombreAppuis, Appuis;
        public NativeArray<byte> Etats;       // 0 en place, 1 tombe, 2 à terre
        public NativeArray<float3> Poussees;  // l'élan donné par le choc à une pierre délogée
        NativeQueue<Impact> impacts;
        NativeQueue<Depot> depots;
        public bool Pret => Etats.IsCreated;
        public bool Chocs = true;             // contre-épreuve : les boulets ne délogent rien
        public int Tombees, Delogees, Tires, AuMur;
        public bool Change;                    // des pierres ont quitté le mur depuis la dernière actualisation

        protected override void OnCreate()
        {
            impacts = new NativeQueue<Impact>(Allocator.Persistent);
            depots = new NativeQueue<Depot>(Allocator.Persistent);
            RequireForUpdate<Relief>();
        }

        protected override void OnDestroy()
        {
            impacts.Dispose(); depots.Dispose();
            if (!Pret) return;
            foreach (var a in new System.IDisposable[] { Centres, Tailles, Orientations, Pans, Couches, Assises, DebutAppuis, NombreAppuis, Appuis, Etats, Poussees })
                a.Dispose();
        }

        protected override void OnUpdate()
        {
            float dt = math.min(SystemAPI.Time.DeltaTime, 1f / 30f);
            if (dt <= 0) return;
            if (!Pret) return;
            var relief = SystemAPI.GetSingleton<Relief>().Blob;
            var dep = Dependency;
            {
                dep = new VolerBoulets { Relief = relief, Dt = dt, Centres = Centres, Tailles = Tailles, Orientations = Orientations, Etats = Etats, Impacts = impacts.AsParallelWriter() }.Schedule(dep);
                dep = new Choquer { Impacts = impacts, Centres = Centres, Etats = Etats, Chocs = Chocs, Tailles = Tailles, Poussees = Poussees }.Schedule(dep);
                dep = new Appuyer { Etats = Etats, DebutAppuis = DebutAppuis, NombreAppuis = NombreAppuis, Appuis = Appuis, Centres = Centres, Tailles = Tailles, Orientations = Orientations, Assises = Assises }.Schedule(dep);
                dep = new Tomber { Relief = relief, Dt = dt, Etats = Etats, Tailles = Tailles, Poussees = Poussees, Depots = depots.AsParallelWriter() }.ScheduleParallel(dep);
            }
            dep.Complete();
            Dependency = default;

            // Les pierres à terre deviennent des gravats : elles relèvent le sol, et l'on marche dessus.
            var b = Bataille.Instance;
            while (depots.TryDequeue(out var d)) { b.Deposer(d.P, d.Volume); Tombees++; Change = true; }
            // Compter ce qui tient encore au mur.
            int n = 0; for (int i = 0; i < Etats.Length; i++) if (Etats[i] == 0) n++;
            if (n != AuMur) { AuMur = n; Change = true; }
        }

        // Un segment de trajectoire contre les pierres encore en place (des boîtes orientées), puis contre le sol.
        [BurstCompile]
        partial struct VolerBoulets : IJobEntity
        {
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            [ReadOnly] public NativeArray<float3> Centres, Tailles;
            [ReadOnly] public NativeArray<quaternion> Orientations;
            [ReadOnly] public NativeArray<byte> Etats;
            public NativeQueue<Impact>.ParallelWriter Impacts;
            public float Dt;

            void Execute(ref Boulet bo, ref LocalTransform t)
            {
                if (bo.Etat == 0) return;
                if (bo.Etat == 2)
                {
                    bo.Vie -= Dt;
                    if (bo.Vie <= 0) { bo.Etat = 0; t = LocalTransform.FromPositionRotationScale(new float3(0, -100, 0), quaternion.identity, 0); }
                    return;
                }
                float3 a = bo.P;
                bo.V.y -= 9.81f * Dt;
                float3 d = bo.V * Dt, fin = a + d;
                float meilleur = 1f; int touche = -1;
                if (Etats.IsCreated)
                    for (int i = 0; i < Etats.Length; i++)
                    {
                        if (Etats[i] != 0) continue;
                        float3 c = Centres[i];
                        if (math.distancesq(c, a) > math.square(math.length(d) + 3f)) continue;
                        var inv = math.inverse(Orientations[i]);
                        float3 o = math.mul(inv, a - c), dl = math.mul(inv, d);
                        float3 h = Tailles[i] * 0.5f + bo.Rayon;
                        // Les dalles : l'entrée et la sortie sur chaque axe.
                        float3 t1 = (-h - o) / dl, t2 = (h - o) / dl;
                        float3 tmin = math.min(t1, t2), tmax = math.max(t1, t2);
                        float entree = math.cmax(tmin), sortie = math.cmin(tmax);
                        if (entree <= sortie && entree >= 0f && entree < meilleur) { meilleur = entree; touche = i; }
                    }
                if (touche >= 0)
                {
                    float3 p = a + d * meilleur;
                    float v2 = math.lengthsq(bo.V);
                    Impacts.Enqueue(new Impact { Pierre = touche, Point = p, Direction = math.normalize(bo.V), Energie = 0.5f * bo.Masse * v2, Quantite = bo.Masse * math.sqrt(v2) });
                    bo.P = p; bo.V = 0; bo.Etat = 2; bo.Vie = 60f;
                }
                else
                {
                    float sol = Sol.Hauteur(ref Relief.Value, fin.xz);
                    if (fin.y - bo.Rayon <= sol) { bo.P = new float3(fin.x, sol + bo.Rayon, fin.z); bo.V = 0; bo.Etat = 2; bo.Vie = 60f; }
                    else bo.P = fin;
                }
                t = LocalTransform.FromPositionRotationScale(bo.P, quaternion.identity, bo.Rayon * 2f);
            }
        }

        // Le choc : l'énergie se répartit dans la maçonnerie autour du point frappé, dans toutes les directions
        // (le long de l'assise, vers les assises voisines et vers les épaisseurs de derrière), d'autant moins
        // que les pierres sont loin ; celles qui en reçoivent plus que ne tient leur mortier sont délogées,
        // poussées dans le sens du tir.
        [BurstCompile]
        struct Choquer : IJob
        {
            public NativeQueue<Impact> Impacts;
            [ReadOnly] public NativeArray<float3> Centres, Tailles;
            public NativeArray<byte> Etats;
            public bool Chocs;
            public NativeArray<float3> Poussees;

            public void Execute()
            {
                while (Impacts.TryDequeue(out var im))
                {
                    if (!Chocs) continue;
                    for (int i = 0; i < Etats.Length; i++)
                    {
                        if (Etats[i] != 0) continue;
                        float d2 = math.distancesq(Centres[i], im.Point);
                        float part = math.exp(-d2 / (Maconnerie.Diffusion * Maconnerie.Diffusion));
                        if (im.Energie * part > Maconnerie.Liaison || i == im.Pierre && im.Energie > Maconnerie.Liaison)
                        {
                            Etats[i] = 1;
                            // La pierre part avec sa part de la quantité de mouvement du boulet.
                            float masse = Tailles[i].x * Tailles[i].y * Tailles[i].z * Maconnerie.Densite;
                            Poussees[i] = im.Direction * math.min(12f, im.Quantite * part / masse);
                        }
                    }
                }
            }
        }

        // Une pierre qui ne repose plus assez sur celles du dessous tombe. Une assise après l'autre, image
        // après image : le mur s'effondre de proche en proche.
        [BurstCompile]
        struct Appuyer : IJob
        {
            public NativeArray<byte> Etats;
            [ReadOnly] public NativeArray<int> DebutAppuis, NombreAppuis, Appuis, Assises;
            [ReadOnly] public NativeArray<float3> Centres, Tailles;
            [ReadOnly] public NativeArray<quaternion> Orientations;

            public void Execute()
            {
                for (int i = 0; i < Etats.Length; i++)
                {
                    if (Etats[i] != 0 || Assises[i] == 0) continue;
                    // Le long du mur (l'axe x de la pierre) : la longueur qui repose sur les pierres en place.
                    float2 moi = Etendue(i);
                    float porte = 0;
                    for (int k = 0; k < NombreAppuis[i]; k++)
                    {
                        int j = Appuis[DebutAppuis[i] + k];
                        if (Etats[j] != 0) continue;
                        float2 lui = Etendue(j);
                        porte += math.max(0f, math.min(moi.y, lui.y) - math.max(moi.x, lui.x));
                    }
                    if (porte < Maconnerie.AppuiMin * (moi.y - moi.x)) Etats[i] = 1;
                }
            }

            float2 Etendue(int i)
            {
                float3 axe = math.mul(Orientations[i], new float3(1, 0, 0));
                float x = math.dot(Centres[i], axe);
                return new float2(x - Tailles[i].x * 0.5f, x + Tailles[i].x * 0.5f);
            }
        }

        // La chute : la pesanteur, un peu de rotation ; au sol, la pierre s'arrête et rejoint les gravats.
        [BurstCompile]
        partial struct Tomber : IJobEntity
        {
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            [NativeDisableParallelForRestriction] public NativeArray<byte> Etats;
            [ReadOnly] public NativeArray<float3> Tailles;
            [ReadOnly] public NativeArray<float3> Poussees;
            public NativeQueue<Depot>.ParallelWriter Depots;
            public float Dt;

            void Execute(ref Pierre p, ref LocalTransform t)
            {
                if (Etats[p.Index] != 1) return;
                if (math.lengthsq(p.Tourne) == 0f)
                {
                    // Au départ de sa chute : un peu d'élan hors du mur, et elle bascule.
                    var alea = Unity.Mathematics.Random.CreateFromIndex((uint)p.Index * 7919u + 17u);
                    p.Tourne = alea.NextFloat3(-1.5f, 1.5f) + 0.01f;
                    p.V += Poussees[p.Index] + alea.NextFloat3(-0.4f, 0.4f);
                }
                p.V.y -= 9.81f * Dt;
                t.Position += p.V * Dt;
                t.Rotation = math.mul(quaternion.EulerXYZ(p.Tourne * Dt), t.Rotation);
                float3 h = Tailles[p.Index];
                float sol = Sol.Hauteur(ref Relief.Value, t.Position.xz);
                if (t.Position.y - 0.5f * math.cmin(h) <= sol)
                {
                    t.Position.y = sol + 0.5f * math.cmin(h);
                    Etats[p.Index] = 2;
                    Depots.Enqueue(new Depot { P = t.Position, Volume = h.x * h.y * h.z });
                }
            }
        }

        // Pour les essais et l'affichage.
        public void Compter(out int enPlace, out int aTerre)
        {
            enPlace = aTerre = 0;
            for (int i = 0; i < Etats.Length; i++) { if (Etats[i] == 0) enPlace++; else if (Etats[i] == 2) aTerre++; }
        }
    }

    // Un engin de siège : il tire à son rythme sur un point du mur. La bombarde tire presque à plat ; le
    // trébuchet lance en cloche. La trajectoire est calculée pour atteindre le point visé ; la dispersion fait le reste.
    public sealed class Engin : MonoBehaviour
    {
        public bool trebuchet;
        public Vector3 cible, etendue;
        public float cadence = 90f, vitesse = 110f, masse = 150f, rayon = 0.25f, dispersion = 0.3f, hauteurBouche = 0.85f;
        public Transform bras;
        public bool actif;
        public int tires;
        float charge, bascule = -1f;
        Unity.Mathematics.Random alea;

        void Start()
        {
            alea = new Unity.Mathematics.Random((uint)(GetInstanceID() * 7 + 1));
            charge = alea.NextFloat(0.2f, 1f) * cadence;
            if (!trebuchet) bras = null;
            else if (bras == null) bras = transform.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "bras");
        }

        void Update()
        {
            if (bascule >= 0f && bras != null)
            {
                bascule += Time.deltaTime;
                // Le bras bascule en une seconde, puis on le rabat pendant le rechargement.
                float u = bascule < 1f ? bascule : math.max(0f, 1f - (bascule - 1f) / (cadence * 0.5f));
                bras.localRotation = Quaternion.Euler(math.lerp(-142f, 40f, math.smoothstep(0f, 1f, u)), 0, 0) * Quaternion.identity;
                if (bascule > cadence * 0.5f + 1f) bascule = -1f;
            }
            if (!actif || Bataille.Instance == null || !Bataille.Instance.Pret) return;
            charge -= Time.deltaTime;
            if (charge > 0) return;
            charge = cadence * alea.NextFloat(0.9f, 1.1f);
            var depart = transform.position + transform.up * (trebuchet ? 12f : hauteurBouche) + transform.forward * (trebuchet ? 3f : 2.2f);
            // On bat une longueur de mur : chaque coup vise un point pris au hasard de part et d'autre du milieu.
            var vise = cible + etendue * alea.NextFloat(-1f, 1f);
            if (!Balistique(depart, vise, vitesse, trebuchet, out var v0)) return;
            // La dispersion : un écart d'angle en hauteur et en direction.
            float s = math.radians(dispersion);
            v0 = Quaternion.AngleAxis(math.degrees(alea.NextFloat(-1f, 1f) * s), Vector3.up) * v0;
            v0 = Quaternion.AngleAxis(math.degrees(alea.NextFloat(-1f, 1f) * s), Vector3.Cross(v0, Vector3.up).normalized) * v0;
            Bataille.Instance.Tirer(depart, v0, masse, rayon);
            tires++;
            if (trebuchet) bascule = 0f;
        }

        // La vitesse de départ pour atteindre un point : l'arc tendu (bombarde) ou l'arc en cloche (trébuchet).
        public static bool Balistique(Vector3 a, Vector3 b, float v, bool cloche, out Vector3 v0)
        {
            const float g = 9.81f;
            var h = new Vector2(b.x - a.x, b.z - a.z);
            float dx = h.magnitude, dy = b.y - a.y, v2 = v * v;
            float disc = v2 * v2 - g * (g * dx * dx + 2f * dy * v2);
            v0 = Vector3.zero;
            if (disc < 0 || dx < 1f) return false;
            float angle = math.atan((v2 + (cloche ? 1f : -1f) * math.sqrt(disc)) / (g * dx));
            var dir = h / dx;
            v0 = new Vector3(dir.x * math.cos(angle), math.sin(angle), dir.y * math.cos(angle)) * v;
            return true;
        }
    }
}
