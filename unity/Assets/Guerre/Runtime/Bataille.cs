using System;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Rendering;
using Unity.Transforms;
using UnityEngine;
using UnityEngine.Rendering;

namespace Guerre
{
    // Lève les deux armées dans le monde ECS et pose le relief pour les jobs.
    // Le nombre d'hommes se change en ligne de commande : -guerre-soldats N.
    public sealed class Bataille : MonoBehaviour
    {
        public Material materiauSoldat;
        public Terrain terrain;
        public int soldats = 10000;
        public int parRegiment = 250;
        public int files = 25;
        public float espacement = 1.1f;

        public static Bataille Instance { get; private set; }
        public bool Pret { get; private set; }
        public int Leves { get; private set; }
        public EntityManager Em => World.DefaultGameObjectInjectionWorld.EntityManager;

        // Bleu roi contre rouge sang : on distingue les camps de loin, par temps de neige.
        static readonly float3[] Camps = { new float3(0.16f, 0.27f, 0.62f), new float3(0.62f, 0.14f, 0.12f) };

        void Awake()
        {
            Instance = this;
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "-guerre-soldats");
            if (i >= 0 && i + 1 < args.Length && int.TryParse(args[i + 1], out int n) && n > 0) soldats = n;
        }

        void Start()
        {
            var em = Em;
            PoserRelief(em);

            var desc = new RenderMeshDescription(ShadowCastingMode.On, receiveShadows: true);
            var rma = new RenderMeshArray(new[] { materiauSoldat }, new[] { Silhouette.Creer() });
            var proto = em.CreateEntity();
            RenderMeshUtility.AddComponents(proto, em, desc, rma, MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(proto, LocalTransform.Identity);
            em.AddComponentData(proto, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(proto, new Soldat());
            em.AddComponentData(proto, new URPMaterialPropertyBaseColor { Value = new float4(1) });

            var t = terrain.transform.position;
            var taille = terrain.terrainData.size;
            float2 centre = new float2(t.x + taille.x / 2, t.z + taille.z / 2);

            int regimentsParCamp = Mathf.CeilToInt(soldats / 2f / parRegiment);
            int restants = soldats;
            var alea = new Unity.Mathematics.Random(1407);
            int rangs = Mathf.CeilToInt(parRegiment / (float)files);
            float largeur = files * espacement, profondeur = rangs * espacement;
            // Deux lignes par armée, dix régiments de front, huit mètres entre eux.
            int deFront = Mathf.Min(10, regimentsParCamp);

            for (int camp = 0; camp < 2; camp++)
            {
                float sens = camp == 0 ? 1f : -1f;              // le camp 0 marche vers +x
                float2 front = new float2(sens, 0);
                for (int k = 0; k < regimentsParCamp && restants > 0; k++)
                {
                    int ligne = k / deFront, rangee = k % deFront;
                    float lateral = (rangee - (deFront - 1) / 2f) * (largeur + 8f);
                    float recul = ligne * (profondeur + 30f);
                    float2 baseP = centre + new float2(-sens * (340f + recul), lateral);
                    float2 avantP = centre + new float2(-sens * (60f + recul), lateral);

                    var reg = em.CreateEntity(typeof(Regiment));
                    em.SetComponentData(reg, new Regiment
                    {
                        Position = baseP, Cible = avantP, Front = front, FrontCible = front,
                        Base = baseP, Avant = avantP, VitesseMarche = 1.25f, Camp = camp, Etape = 1
                    });

                    int nb = Mathf.Min(parRegiment, restants);
                    restants -= nb;
                    float3 teinteRegiment = Camps[camp] * (0.85f + 0.3f * alea.NextFloat());
                    var hommes = em.Instantiate(proto, nb, Allocator.Temp);
                    for (int h = 0; h < nb; h++)
                    {
                        int f = h % files, rg = h / files;
                        float2 place = new float2((f - (files - 1) / 2f) * espacement, -(rg - (rangs - 1) / 2f) * espacement);
                        place += alea.NextFloat2(-0.12f, 0.12f);
                        float2 p = baseP + new float2(front.y, -front.x) * place.x + front * place.y;
                        float y = Sol.Hauteur(ref relief.Value, p);
                        em.SetComponentData(hommes[h], new Soldat
                        {
                            Regiment = reg, Place = place, Allure = alea.NextFloat(0.9f, 1.1f),
                            Phase = alea.NextFloat(0, 6.28f),
                            Teinte = teinteRegiment * alea.NextFloat(0.85f, 1.15f)
                        });
                        em.SetComponentData(hommes[h], LocalTransform.FromPositionRotation(
                            new float3(p.x, y, p.y), quaternion.LookRotationSafe(new float3(front.x, 0, front.y), math.up())));
                    }
                    hommes.Dispose();
                }
            }
            em.DestroyEntity(proto);
            Leves = soldats - restants;
            Pret = true;
        }

        Entity reliefEntite;
        BlobAssetReference<ReliefBlob> relief;

        void PoserRelief(EntityManager em)
        {
            var td = terrain.terrainData;
            int n = td.heightmapResolution;
            float[,] h = td.GetHeights(0, 0, n, n);
            using var b = new BlobBuilder(Allocator.Temp);
            ref var root = ref b.ConstructRoot<ReliefBlob>();
            var arr = b.Allocate(ref root.Hauteurs, n * n);
            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                    arr[z * n + x] = h[z, x] * td.size.y;
            root.Resolution = n;
            // Le Terrain de Unity est carré ici ; la vallée est construite ainsi.
            root.Taille = td.size.x;
            root.Origine = terrain.transform.position;
            relief = b.CreateBlobAssetReference<ReliefBlob>(Allocator.Persistent);
            reliefEntite = em.CreateEntity(typeof(Relief));
            em.SetComponentData(reliefEntite, new Relief { Blob = relief });
        }

        void OnDestroy()
        {
            if (World.DefaultGameObjectInjectionWorld == null || !World.DefaultGameObjectInjectionWorld.IsCreated) return;
            Em.CompleteAllTrackedJobs();
            if (relief.IsCreated) relief.Dispose();
        }

        // Régiment d'un camp le plus proche d'un point, pour la sélection.
        public Entity RegimentProche(float2 p, int camp, float rayonMax)
        {
            var q = Em.CreateEntityQuery(typeof(Regiment));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var regs = q.ToComponentDataArray<Regiment>(Allocator.Temp);
            Entity best = Entity.Null; float bd = rayonMax;
            for (int i = 0; i < ents.Length; i++)
            {
                if (regs[i].Camp != camp) continue;
                float d = math.distance(regs[i].Position, p);
                if (d < bd) { bd = d; best = ents[i]; }
            }
            return best;
        }
    }
}
