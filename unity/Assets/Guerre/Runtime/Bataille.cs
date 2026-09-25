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
        // Une variante par arme : piquier, hallebardier, arbalétrier, cavalier (fabrique/soldats.py).
        public Material[] materiaux;
        public Mesh[] maillages;
        public Material materiauCarreau, materiauPavois;
        public const int Carreaux = 8192;   // le réservoir : carreaux en vol et plantés, réutilisés
        public Terrain terrain;
        public int soldats = 10000;
        public int parRegiment = 250;
        public int files = 25;
        public float espacement = 1.1f;

        public static Bataille Instance { get; private set; }
        public bool Pret { get; private set; }
        public int Leves { get; private set; }
        public EntityManager Em => World.DefaultGameObjectInjectionWorld.EntityManager;
        bool sansCorps, sansPoussee, sansPeur, sansPavois, sansMasse, sansPiques;
        public const int FilesCavalerie = 35;

        // Bleu roi contre rouge sang : on distingue les camps de loin, par temps de neige.
        static readonly float3[] Camps = { new float3(0.16f, 0.27f, 0.62f), new float3(0.62f, 0.14f, 0.12f) };

        public const float PasSimulation = 1f / 60f;

        void Awake()
        {
            Instance = this;
            // La simulation avance à pas fixe, quelle que soit la cadence d'affichage : sans cela,
            // la poussée et la peur donneraient d'autres issues sur une machine plus lente.
            World.DefaultGameObjectInjectionWorld.GetExistingSystemManaged<SimulationSystemGroup>().RateManager =
                new RateUtils.FixedRateCatchUpManager(PasSimulation);
            var args = Environment.GetCommandLineArgs();
            int i = Array.LastIndexOf(args, "-guerre-soldats");   // la dernière valeur l'emporte
            if (i >= 0 && i + 1 < args.Length && int.TryParse(args[i + 1], out int n) && n > 0) soldats = n;
            sansCorps = Array.IndexOf(args, "-guerre-sans-corps") >= 0;
            sansPoussee = Array.IndexOf(args, "-guerre-sans-poussee") >= 0;
            sansPeur = Array.IndexOf(args, "-guerre-sans-peur") >= 0;
            sansPavois = Array.IndexOf(args, "-guerre-sans-pavois") >= 0;
            sansMasse = Array.IndexOf(args, "-guerre-sans-masse") >= 0;
            sansPiques = Array.IndexOf(args, "-guerre-sans-piques") >= 0;
            // Contre-épreuve de la mesure : le shader ignore l'animation cuite.
            if (Array.IndexOf(args, "-guerre-sans-animation") >= 0)
                foreach (var m in materiaux) m.SetFloat("_VATActif", 0);
        }

        void Start()
        {
            var em = Em;
            PoserRelief(em);
            var reglages = em.CreateEntity(typeof(ReglagesSimulation));
            em.SetComponentData(reglages, new ReglagesSimulation { Corps = (byte)(sansCorps ? 0 : 1), Poussee = (byte)(sansPoussee ? 0 : 1), Peur = (byte)(sansPeur ? 0 : 1), Pavois = (byte)(sansPavois ? 0 : 1),
                Masse = (byte)(sansMasse ? 0 : 1), Piques = (byte)(sansPiques ? 0 : 1) });

            var desc = new RenderMeshDescription(ShadowCastingMode.On, receiveShadows: true);
            var rma = new RenderMeshArray(materiaux, maillages);
            var proto = em.CreateEntity();
            RenderMeshUtility.AddComponents(proto, em, desc, rma, MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(proto, LocalTransform.Identity);
            em.AddComponentData(proto, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(proto, new Soldat());
            em.AddComponentData(proto, new URPMaterialPropertyBaseColor { Value = new float4(1) });
            em.AddComponentData(proto, new AnimEtat());
            em.AddComponentData(proto, new AnimCombat());
            em.CreateEntity(typeof(CompteTir));

            // Le pavois : un panneau de bois peint aux couleurs du camp.
            var protoPavois = em.CreateEntity();
            RenderMeshUtility.AddComponents(protoPavois, em, desc, new RenderMeshArray(new[] { materiauPavois }, new[] { Boite(Armes.PavoisLargeur, Armes.PavoisHauteur, 0.05f, 0f) }),
                MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(protoPavois, LocalTransform.Identity);
            em.AddComponentData(protoPavois, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(protoPavois, new Pavois());
            em.AddComponentData(protoPavois, new URPMaterialPropertyBaseColor { Value = new float4(1) });

            var t = terrain.transform.position;
            var taille = terrain.terrainData.size;
            float2 centre = new float2(t.x + taille.x / 2, t.z + taille.z / 2);

            int regimentsParCamp = Mathf.CeilToInt(soldats / 2f / parRegiment);
            int restants = soldats;
            var alea = new Unity.Mathematics.Random(1407);
            int rangs = Mathf.CeilToInt(parRegiment / (float)files);
            int index = 0;
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
                    // Au premier rang, piques et hallebardes alternent ; les arbalétriers tiennent la seconde
                    // ligne, et la cavalerie en couvre les ailes.
                    bool aile = ligne == 1 && deFront >= 4 && (rangee == 0 || rangee == deFront - 1);
                    int arme = ligne == 0 ? rangee % 2 : aile ? Corps.Cavalier : 2;
                    float lateral = (rangee - (deFront - 1) / 2f) * (largeur + 8f) + (aile ? math.sign(rangee - (deFront - 1) / 2f) * 10f : 0f);
                    float recul = ligne * (profondeur + 30f);
                    float2 baseP = centre + new float2(-sens * (340f + recul), lateral);
                    float2 avantP = centre + new float2(-sens * (60f + recul), lateral);

                    int nb = Mathf.Min(parRegiment, restants);
                    restants -= nb;
                    var reg = em.CreateEntity(typeof(Regiment));
                    var donnees = new Regiment
                    {
                        Position = baseP, Cible = avantP, Front = front, FrontCible = front,
                        Base = baseP, Avant = avantP, VitesseMarche = 1.25f, Camp = camp, Etape = 1,
                        Files = aile ? FilesCavalerie : files, Effectif = nb, Espacement = espacement, Index = index++, Arme = arme
                    };
                    em.SetComponentData(reg, donnees);
                    float3 teinteRegiment = Camps[camp] * (0.85f + 0.3f * alea.NextFloat());
                    var hommes = em.Instantiate(proto, nb, Allocator.Temp);
                    for (int h = 0; h < nb; h++)
                    {
                        float2 decalage = alea.NextFloat2(-0.12f, 0.12f);
                        float2 p = Formation.VersMonde(Formation.Place(donnees, h) + decalage, baseP, front);
                        float y = Sol.Hauteur(ref relief.Value, p);
                        em.SetComponentData(hommes[h], new Soldat
                        {
                            Regiment = reg, Numero = h, Decalage = decalage, Allure = alea.NextFloat(0.9f, 1.1f),
                            Phase = alea.NextFloat(0, 6.28f),
                            Teinte = teinteRegiment * alea.NextFloat(0.85f, 1.15f),
                            Camp = (byte)camp, Arme = (byte)arme, Sante = 1, Recharge = alea.NextFloat(0.5f, 2.5f),
                            // Le courage varie d'un homme à l'autre : les premiers à fuir entraînent les autres.
                            Courage = alea.NextFloat(0.55f, 0.9f)
                        });
                        em.SetComponentData(hommes[h], MaterialMeshInfo.FromRenderMeshArrayIndices(arme, arme));
                        em.SetComponentData(hommes[h], LocalTransform.FromPositionRotation(
                            new float3(p.x, y, p.y), quaternion.LookRotationSafe(new float3(front.x, 0, front.y), math.up())));
                    }
                    if (arme == 2)
                    {
                        var pavois = em.Instantiate(protoPavois, nb, Allocator.Temp);
                        for (int h = 0; h < nb; h++)
                        {
                            em.SetComponentData(pavois[h], new Pavois { Porteur = hommes[h] });
                            em.SetComponentData(pavois[h], new URPMaterialPropertyBaseColor { Value = new float4(math.lerp(Camps[camp], new float3(0.85f, 0.8f, 0.7f), 0.35f), 1) });
                        }
                        pavois.Dispose();
                    }
                    hommes.Dispose();
                }
            }
            em.DestroyEntity(proto);
            em.DestroyEntity(protoPavois);

            // Le réservoir de carreaux, rangés sous le terrain jusqu'à leur tir.
            var protoCarreau = em.CreateEntity();
            var descCarreau = new RenderMeshDescription(ShadowCastingMode.Off, receiveShadows: false);
            RenderMeshUtility.AddComponents(protoCarreau, em, descCarreau, new RenderMeshArray(new[] { materiauCarreau }, new[] { Boite(0.025f, 0.025f, 0.42f, -0.0125f) }),
                MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(protoCarreau, LocalTransform.FromPositionRotationScale(new float3(0, -100, 0), quaternion.identity, 0));
            em.AddComponentData(protoCarreau, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(protoCarreau, new Projectile());
            em.Instantiate(protoCarreau, Carreaux, Allocator.Temp).Dispose();
            em.DestroyEntity(protoCarreau);
            Leves = soldats - restants;
            Pret = true;
        }

        // Une boîte centrée en x et z, posée sur y = bas.
        static Mesh Boite(float lx, float ly, float lz, float bas)
        {
            var m = new Mesh { name = "Boite" };
            float x = lx / 2, z = lz / 2, y0 = bas, y1 = bas + ly;
            var v = new System.Collections.Generic.List<Vector3>();
            var tri = new System.Collections.Generic.List<int>();
            void Face(Vector3 a, Vector3 b, Vector3 c, Vector3 d)
            {
                int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d);
                tri.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            }
            Face(new Vector3(-x, y0, -z), new Vector3(-x, y1, -z), new Vector3(x, y1, -z), new Vector3(x, y0, -z));
            Face(new Vector3(x, y0, z), new Vector3(x, y1, z), new Vector3(-x, y1, z), new Vector3(-x, y0, z));
            Face(new Vector3(-x, y0, z), new Vector3(-x, y1, z), new Vector3(-x, y1, -z), new Vector3(-x, y0, -z));
            Face(new Vector3(x, y0, -z), new Vector3(x, y1, -z), new Vector3(x, y1, z), new Vector3(x, y0, z));
            Face(new Vector3(-x, y1, -z), new Vector3(-x, y1, z), new Vector3(x, y1, z), new Vector3(x, y1, -z));
            Face(new Vector3(-x, y0, z), new Vector3(-x, y0, -z), new Vector3(x, y0, -z), new Vector3(x, y0, z));
            m.SetVertices(v); m.SetTriangles(tri, 0);
            m.RecalculateNormals(); m.RecalculateBounds();
            return m;
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

        // Les régiments d'un camp (tous si camp < 0), avec leurs données du moment.
        public (Entity e, Regiment r)[] Regiments(int camp = -1)
        {
            var q = Em.CreateEntityQuery(typeof(Regiment));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var regs = q.ToComponentDataArray<Regiment>(Allocator.Temp);
            var l = new System.Collections.Generic.List<(Entity, Regiment)>();
            for (int i = 0; i < ents.Length; i++)
                if (camp < 0 || regs[i].Camp == camp) l.Add((ents[i], regs[i]));
            return l.ToArray();
        }

        // Le régiment sous un point du sol : dans son emprise (à trois mètres près),
        // sinon le plus proche dans le rayon donné.
        public Entity RegimentSous(float2 p, int camp, float rayonMax)
        {
            Entity best = Entity.Null; float bd = rayonMax;
            foreach (var (e, r) in Regiments(camp))
            {
                float2 d = p - r.Position, droite = new float2(r.Front.y, -r.Front.x);
                if (math.abs(math.dot(d, droite)) <= r.Largeur / 2 + 3 && math.abs(math.dot(d, r.Front)) <= r.Profondeur / 2 + 3) return e;
                float l = math.length(d);
                if (l < bd) { bd = l; best = e; }
            }
            return best;
        }

        // Un ordre : aller à un point, y faire face à une direction, sur tant de files.
        // Le scénario de démonstration cesse pour ce régiment.
        public void Ordonner(Entity e, float2 cible, float2 front, int files) =>
            Ordonner(new[] { (e, cible, front, files) });

        public void Ordonner(System.Collections.Generic.IEnumerable<(Entity e, float2 cible, float2 front, int files)> ordres)
        {
            var liste = new System.Collections.Generic.List<Entity>();
            foreach (var (e, cible, front, files) in ordres)
            {
                var r = Em.GetComponentData<Regiment>(e);
                r.Cible = cible;
                if (math.lengthsq(front) > 1e-4f) r.FrontCible = math.normalize(front);
                r.Files = math.clamp(files, 1, r.Effectif);
                r.Ordonne = 1;
                r.Ennemi = Entity.Null;   // un ordre de marche rompt l'attaque
                Em.SetComponentData(e, r);
                liste.Add(e);
            }
            Rangs.Reclasser(Em, liste);
        }

        // Attaquer : chaque régiment prend l'ancre de l'ennemi pour cible et y pousse ses hommes.
        public void Attaquer(System.Collections.Generic.IEnumerable<Entity> regiments, Entity ennemi)
        {
            foreach (var e in regiments)
            {
                var r = Em.GetComponentData<Regiment>(e);
                r.Ennemi = ennemi;
                r.Ordonne = 1;
                Em.SetComponentData(e, r);
            }
        }

        // Pour les essais : pose un régiment formé à un endroit, sans marche d'approche.
        public void Deplacer(Entity e, float2 ancre, float2 front, int files)
        {
            var em = Em;
            em.CompleteAllTrackedJobs();
            var r = em.GetComponentData<Regiment>(e);
            r.Position = r.Cible = ancre; r.Front = r.FrontCible = math.normalize(front);
            r.Files = math.clamp(files, 1, math.max(1, r.Effectif)); r.Ordonne = 1; r.Ennemi = Entity.Null;
            em.SetComponentData(e, r);
            var q = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var sold = q.ToComponentDataArray<Soldat>(Allocator.Temp);
            for (int i = 0; i < ents.Length; i++)
            {
                if (sold[i].Regiment != e) continue;
                var s = sold[i];
                s.Vitesse = 0; s.Numero = math.min(s.Numero, r.Effectif - 1);
                em.SetComponentData(ents[i], s);
                float2 p = Formation.VersMonde(Formation.Place(r, s.Numero) + s.Decalage, ancre, r.Front);
                em.SetComponentData(ents[i], LocalTransform.FromPositionRotation(new float3(p.x, Sol.Hauteur(ref relief.Value, p), p.y),
                    quaternion.LookRotationSafe(new float3(r.Front.x, 0, r.Front.y), math.up())));
            }
        }

        // Pour les essais : retire des hommes d'un régiment (ils n'ont jamais été levés).
        public void Reduire(Entity e, int retires)
        {
            var em = Em;
            em.CompleteAllTrackedJobs();
            var q = em.CreateEntityQuery(typeof(Soldat));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var sold = q.ToComponentDataArray<Soldat>(Allocator.Temp);
            var aRetirer = new System.Collections.Generic.List<Entity>();
            for (int i = 0; i < ents.Length && aRetirer.Count < retires; i++)
                if (sold[i].Regiment == e) aRetirer.Add(ents[i]);
            var partis = new System.Collections.Generic.HashSet<Entity>(aRetirer);
            var qp = em.CreateEntityQuery(typeof(Pavois));
            using (var pe = qp.ToEntityArray(Allocator.Temp))
            using (var pd = qp.ToComponentDataArray<Pavois>(Allocator.Temp))
                for (int i = 0; i < pe.Length; i++) if (partis.Contains(pd[i].Porteur)) em.DestroyEntity(pe[i]);
            foreach (var x in aRetirer) em.DestroyEntity(x);
            Leves -= aRetirer.Count;
            Rangs.Reclasser(em, new System.Collections.Generic.List<Entity> { e });
        }

        // Pour les essais : même arme pour tous les hommes d'un régiment, pour comparer à armes égales.
        public void Armer(Entity e, int arme)
        {
            var em = Em;
            em.CompleteAllTrackedJobs();
            var r = em.GetComponentData<Regiment>(e);
            r.Arme = arme;
            em.SetComponentData(e, r);
            var q = em.CreateEntityQuery(typeof(Soldat));
            using var ents = q.ToEntityArray(Allocator.Temp);
            using var sold = q.ToComponentDataArray<Soldat>(Allocator.Temp);
            var hommes = new System.Collections.Generic.HashSet<Entity>();
            for (int i = 0; i < ents.Length; i++)
            {
                if (sold[i].Regiment != e) continue;
                var s = sold[i]; s.Arme = (byte)arme;
                em.SetComponentData(ents[i], s);
                em.SetComponentData(ents[i], MaterialMeshInfo.FromRenderMeshArrayIndices(arme, arme));
                hommes.Add(ents[i]);
            }
            // Seul l'arbalétrier porte un pavois.
            if (arme == 2) return;
            var qp = em.CreateEntityQuery(typeof(Pavois));
            using var pe = qp.ToEntityArray(Allocator.Temp);
            using var pd = qp.ToComponentDataArray<Pavois>(Allocator.Temp);
            for (int i = 0; i < pe.Length; i++) if (hommes.Contains(pd[i].Porteur)) em.DestroyEntity(pe[i]);
        }

        public void Choisir(Entity e, bool choisi)
        {
            var r = Em.GetComponentData<Regiment>(e);
            r.Selection = (byte)(choisi ? 1 : 0);
            Em.SetComponentData(e, r);
        }
    }
}
