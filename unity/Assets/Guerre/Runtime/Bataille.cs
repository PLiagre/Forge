using System;
using System.Collections.Generic;
using System.Linq;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
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
        public CarteDonnees carte;          // les murs, les maisons, les ponts et les lieux nommés (Construire.cs)
        public int soldats = 10000;
        public int parRegiment = 250;
        public int files = 25;
        public float espacement = 1.1f;

        public static Bataille Instance { get; private set; }
        public bool Pret { get; private set; }
        public int Leves { get; private set; }
        public EntityManager Em => World.DefaultGameObjectInjectionWorld.EntityManager;
        bool sansCorps, sansPoussee, sansPeur, sansPavois, sansMasse, sansPiques, sansPont, sansMurs, sansChocs;
        public Planificateur Planificateur { get; private set; }
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
            sansPont = Array.IndexOf(args, "-guerre-sans-pont") >= 0;
            sansMurs = Array.IndexOf(args, "-guerre-sans-murs") >= 0;
            sansChocs = Array.IndexOf(args, "-guerre-sans-chocs") >= 0;
            // Contre-épreuve de la mesure : le shader ignore l'animation cuite.
            if (Array.IndexOf(args, "-guerre-sans-animation") >= 0)
                foreach (var m in materiaux) m.SetFloat("_VATActif", 0);
        }

        void Start()
        {
            var em = Em;
            PoserRelief(em);
            LeverMurs(em);
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
                    var reg = em.CreateEntity(typeof(Regiment), typeof(PointChemin));
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

        Entity reliefEntite, obstaclesEntite;
        BlobAssetReference<ReliefBlob> relief;
        // Le relief lu par la simulation, gardé ici pour qu'on puisse y ajouter les gravats.
        float[] hauteurs;
        int resolution;
        float taille;
        float3 origineRelief;

        void PoserRelief(EntityManager em)
        {
            var td = terrain.terrainData;
            int n = td.heightmapResolution;
            float[,] h = td.GetHeights(0, 0, n, n);
            resolution = n; taille = td.size.x; origineRelief = terrain.transform.position;
            hauteurs = new float[n * n];
            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                    hauteurs[z * n + x] = h[z, x] * td.size.y;
            // Les tabliers des ponts : le sol sur lequel on marche passe au-dessus du ravin.
            if (carte != null && !sansPont)
                foreach (var tb in carte.tabliers)
                {
                    float pas = taille / (n - 1);
                    for (int z = 0; z < n; z++)
                        for (int x = 0; x < n; x++)
                        {
                            var p = new Vector2(origineRelief.x + x * pas, origineRelief.z + z * pas);
                            if (CarteDonnees.Dans(new CarteDonnees.Bloc { centre = tb.centre, demi = tb.demi, angle = tb.angle }, p))
                                hauteurs[z * n + x] = tb.hauteur - origineRelief.y;
                        }
                }
            relief = CreerRelief();
            reliefEntite = em.CreateEntity(typeof(Relief));
            em.SetComponentData(reliefEntite, new Relief { Blob = relief });
            PoserObstacles(em, td.size.x);
        }

        BlobAssetReference<ReliefBlob> CreerRelief()
        {
            using var b = new BlobBuilder(Allocator.Temp);
            ref var root = ref b.ConstructRoot<ReliefBlob>();
            var arr = b.Allocate(ref root.Hauteurs, hauteurs.Length);
            for (int i = 0; i < hauteurs.Length; i++) arr[i] = hauteurs[i];
            root.Resolution = resolution;
            // Le Terrain de Unity est carré ici ; la vallée est construite ainsi.
            root.Taille = taille;
            root.Origine = origineRelief;
            return b.CreateBlobAssetReference<ReliefBlob>(Allocator.Persistent);
        }

        BlobAssetReference<ObstaclesBlob> obstacles;
        public const float PenteMax = 0.84f;   // 40° : au-delà, on ne tient pas debout, on ne monte pas
        public const float Passage = 2f;       // m : une pierre qui barre cette hauteur au-dessus du sol barre le passage
        // La grille, au mètre, et ce qui la compose : les pentes, les emprises des bâtiments (et la porte fermée),
        // les pierres des pans de mur encore en place.
        byte[] pentes, statiques, murs, cases;
        int cote;
        float2 origineCases;

        // La grille des obstacles, au mètre : les pentes trop raides, puis les emprises des murs, des tours et
        // des maisons. Le planificateur des chemins lit la même grille.
        void PoserObstacles(EntityManager em, float c)
        {
            cote = Mathf.CeilToInt(c);
            int total = cote * cote;
            origineCases = new float2(terrain.transform.position.x, terrain.transform.position.z);
            pentes = Pentes(0, 0, cote, cote);
            statiques = new byte[total];
            murs = new byte[total];
            cases = new byte[total];
            if (carte != null && !sansMurs)
                foreach (var bl in carte.blocs) Tracer(statiques, cote, origineCases, bl);
            for (int i = 0; i < total; i++) cases[i] = (byte)(pentes[i] | statiques[i]);
            obstacles = CreerObstacles();
            obstaclesEntite = em.CreateEntity(typeof(Obstacles));
            em.SetComponentData(obstaclesEntite, new Obstacles { Blob = obstacles });
            Planificateur = new Planificateur(cases, cote, cote, new Vector2(origineCases.x, origineCases.y));
        }

        // Les cases trop raides d'une fenêtre de la grille, calculées sur le relief du moment.
        byte[] Pentes(int x0, int y0, int l, int h)
        {
            var bloque = new NativeArray<byte>(l * h, Allocator.TempJob);
            new CalculerPentes { Relief = relief, Bloque = bloque, Largeur = l, Origine = origineCases + new float2(x0, y0), Pas = 1f, PenteMax = PenteMax }
                .Schedule(l * h, 4096).Complete();
            var r = bloque.ToArray();
            bloque.Dispose();
            if (l == cote && h == cote) return r;
            for (int y = 0; y < h; y++) for (int x = 0; x < l; x++) pentes[(y0 + y) * cote + x0 + x] = r[y * l + x];
            return pentes;
        }

        BlobAssetReference<ObstaclesBlob> CreerObstacles()
        {
            using var b = new BlobBuilder(Allocator.Temp);
            ref var root = ref b.ConstructRoot<ObstaclesBlob>();
            var arr = b.Allocate(ref root.Bloque, cases.Length);
            for (int i = 0; i < cases.Length; i++) arr[i] = cases[i];
            root.Largeur = root.Hauteur = cote; root.Origine = origineCases; root.Pas = 1f;
            return b.CreateBlobAssetReference<ObstaclesBlob>(Allocator.Persistent);
        }

        // Les cases dont le centre tombe dans l'emprise d'un bloc.
        public static void Tracer(byte[] cases, int l, float2 origine, CarteDonnees.Bloc bl)
        {
            float r = bl.demi.magnitude;
            int x0 = Mathf.Max(0, Mathf.FloorToInt(bl.centre.x - r - origine.x)), x1 = Mathf.Min(l - 1, Mathf.CeilToInt(bl.centre.x + r - origine.x));
            int y0 = Mathf.Max(0, Mathf.FloorToInt(bl.centre.y - r - origine.y)), y1 = Mathf.Min(l - 1, Mathf.CeilToInt(bl.centre.y + r - origine.y));
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                    if (CarteDonnees.Dans(bl, new Vector2(origine.x + x + 0.5f, origine.y + y + 0.5f))) cases[y * l + x] = 1;
        }

        // ————— Le siège : les pans de mur appareillés, les boulets, les gravats, la porte. —————

        public Material materiauPierre;
        public GameObject bombarde, trebuchet;
        SystemeMurs systemeMurs;
        readonly List<Entity> boulets = new List<Entity>();
        int prochainBoulet;
        RectInt fenetreMurs;          // la partie de la grille que les pans de mur et leurs gravats peuvent changer
        bool reliefChange;
        float prochaineActualisation;
        public bool PorteFermee { get; private set; }

        // Les matériaux du rempart du kit : basalte, pierre de taille, neige (Construire.cs).
        public Material[] materiauxMur;
        public const int Basalte = 0, PierreDeTaille = 1, Neige = 2;
        // Les parties d'un pan (SystemeMurs.Couches) : les trois épaisseurs du mur, puis ce qui le couronne.
        public const int Exterieur = 0, Blocage = 1, Interieur = 2, Contrefort = 3, Dalle = 4, NeigeDalle = 5, Merlon = 6, Coiffe = 7;

        // Chaque pan reproduit, pierre à pierre, le module rempart_10m du kit de Forge (local3d/citadelle/assets.py,
        // wall()) : un corps de 2,7 m en trois épaisseurs (parement extérieur, blocage, parement intérieur), des
        // assises de 0,70 m en pierres de 1,30 m posées à joints croisés, un parement de basalte semé de pierre de
        // taille ; deux contreforts devant ; une dalle, sa neige, et cinq merlons coiffés de neige. Chaque pierre
        // repose sur celles, dessous, dont l'empreinte chevauche la sienne.
        void LeverMurs(EntityManager em)
        {
            systemeMurs = World.DefaultGameObjectInjectionWorld.GetExistingSystemManaged<SystemeMurs>();
            if (carte == null || carte.pans.Count == 0 || materiauxMur == null || materiauxMur.Length < 3) return;
            var centres = new List<float3>(); var tailles = new List<float3>(); var rots = new List<quaternion>();
            var pans = new List<int>(); var couches = new List<int>(); var assises = new List<int>(); var mats = new List<int>();
            var alea = new Unity.Mathematics.Random(1415);
            float xmin = float.MaxValue, xmax = float.MinValue, zmin = float.MaxValue, zmax = float.MinValue;
            const float Pas = 1.3f, JointH = 0.07f, JointL = 0.06f;
            for (int k = 0; k < carte.pans.Count; k++)
            {
                var pan = carte.pans[k];
                float phi = math.radians(pan.exterieur);
                float3 n = new float3(math.cos(phi), 0, math.sin(phi));   // vers l'extérieur
                var q = quaternion.LookRotationSafe(n, math.up());
                float3 axe = math.mul(q, new float3(1, 0, 0));
                float3 pied = pan.pied;
                float L = pan.longueur;
                // Une pierre, dans le repère du pan : x le long du mur, y au-dessus du pied, z vers l'extérieur.
                void Poser(float x, float y, float z, float3 t, int couche, int assise, int mat)
                {
                    float3 p = pied + axe * x + n * z + new float3(0, y, 0);
                    centres.Add(p); tailles.Add(t); rots.Add(q); pans.Add(k); couches.Add(couche); assises.Add(assise); mats.Add(mat);
                    xmin = math.min(xmin, p.x); xmax = math.max(xmax, p.x); zmin = math.min(zmin, p.z); zmax = math.max(zmax, p.z);
                }
                // Le corps : les assises, jusque sous la dalle.
                int nAssises = Mathf.RoundToInt(pan.hauteur / 0.7f);
                float h = pan.hauteur / nAssises, ep = pan.epaisseur / 3f;
                for (int c = 0; c < 3; c++)
                    for (int a = 0; a < nAssises; a++)
                    {
                        // Joints croisés d'une assise à l'autre, et d'une épaisseur à l'autre.
                        float decale = ((a + c) & 1) * Pas / 2;
                        var bords = new List<float> { -L / 2 };
                        for (float b = -L / 2 + (decale > 0 ? decale : Pas); b < L / 2 - 0.3f; b += Pas) bords.Add(b);
                        bords.Add(L / 2);
                        for (int s = 0; s + 1 < bords.Count; s++)
                        {
                            float x0 = bords[s], x1 = bords[s + 1];
                            // Le parement extérieur est de basalte semé de pierre de taille, comme celui du kit.
                            int mat = c == Exterieur && alea.NextFloat() < 0.22f ? PierreDeTaille : Basalte;
                            Poser((x0 + x1) / 2, (a + 0.5f) * h, (1 - c) * ep, new float3(x1 - x0 - JointL, h - JointH, ep - 0.04f), c, a, mat);
                        }
                    }
                // Les contreforts, devant le mur.
                int nC = Mathf.RoundToInt(9.6f / h);
                foreach (float x in new[] { -3.3f, 3.3f })
                    for (int a = 0; a < nC; a++)
                        Poser(x, (a + 0.5f) * h, pan.epaisseur / 2 + 0.55f, new float3(1.0f - JointL, h - JointH, 1.25f - 0.04f), Contrefort, a, Basalte);
                // La dalle qui couvre le mur, et sa neige.
                float dessus = nAssises * h;
                for (float x0 = -L / 2; x0 < L / 2 - 0.01f; x0 += Pas)
                {
                    float x1 = math.min(L / 2, x0 + Pas);
                    Poser((x0 + x1) / 2, dessus + 0.225f, 0, new float3(x1 - x0 - 0.02f, 0.45f - 0.02f, 3.1f), Dalle, nAssises, PierreDeTaille);
                    Poser((x0 + x1) / 2, dessus + 0.5f, 0, new float3(x1 - x0 - 0.02f, 0.1f, 2.2f), NeigeDalle, nAssises + 1, Neige);
                }
                // Les merlons, du côté de la campagne, et leurs coiffes de neige.
                foreach (float x in new[] { -4f, -2f, 0f, 2f, 4f })
                {
                    Poser(x, dessus + 0.45f + 0.6875f, 0.95f, new float3(1.15f, 1.375f, 1.25f), Merlon, nAssises + 1, PierreDeTaille);
                    Poser(x, dessus + 0.45f + 1.375f + 0.075f, 0.95f, new float3(1.22f, 0.15f, 1.32f), Coiffe, nAssises + 2, Neige);
                }
            }
            int nb = centres.Count;
            // Les appuis : dans le même pan, les pierres dont le dessus touche le dessous de celle-ci, avec la surface
            // de leur empreinte commune. Une pierre posée au sol n'a pas d'appui : elle ne tombe pas faute d'appui.
            var debut = new int[nb]; var nombre = new int[nb]; var appuis = new List<int>(); var aires = new List<float>();
            var aire = new float[nb];
            float2 Plan(int i)
            {
                var pan = carte.pans[pans[i]];
                float phi = math.radians(pan.exterieur);
                float3 n = new float3(math.cos(phi), 0, math.sin(phi)), axe = math.mul(rots[i], new float3(1, 0, 0));
                float3 d = centres[i] - (float3)pan.pied;
                return new float2(math.dot(d, axe), math.dot(d, n));
            }
            var plans = new float2[nb];
            for (int i = 0; i < nb; i++) { plans[i] = Plan(i); aire[i] = tailles[i].x * tailles[i].z; }
            for (int i = 0; i < nb; i++)
            {
                debut[i] = appuis.Count;
                float bas = centres[i].y - tailles[i].y / 2 - carte.pans[pans[i]].pied.y;
                if (bas > 0.02f)
                    for (int j = 0; j < nb; j++)
                    {
                        if (j == i || pans[j] != pans[i]) continue;
                        float hautJ = centres[j].y + tailles[j].y / 2;
                        if (math.abs(hautJ - (centres[i].y - tailles[i].y / 2)) > 0.08f) continue;
                        float2 a = plans[i], b = plans[j];
                        float ox = math.min(a.x + tailles[i].x / 2, b.x + tailles[j].x / 2) - math.max(a.x - tailles[i].x / 2, b.x - tailles[j].x / 2);
                        float oz = math.min(a.y + tailles[i].z / 2, b.y + tailles[j].z / 2) - math.max(a.y - tailles[i].z / 2, b.y - tailles[j].z / 2);
                        if (ox > 0.01f && oz > 0.01f) { appuis.Add(j); aires.Add(ox * oz); }
                    }
                nombre[i] = appuis.Count - debut[i];
            }
            systemeMurs.Centres = new NativeArray<float3>(centres.ToArray(), Allocator.Persistent);
            systemeMurs.Tailles = new NativeArray<float3>(tailles.ToArray(), Allocator.Persistent);
            systemeMurs.Orientations = new NativeArray<quaternion>(rots.ToArray(), Allocator.Persistent);
            systemeMurs.Pans = new NativeArray<int>(pans.ToArray(), Allocator.Persistent);
            systemeMurs.Couches = new NativeArray<int>(couches.ToArray(), Allocator.Persistent);
            systemeMurs.Assises = new NativeArray<int>(assises.ToArray(), Allocator.Persistent);
            systemeMurs.DebutAppuis = new NativeArray<int>(debut, Allocator.Persistent);
            systemeMurs.NombreAppuis = new NativeArray<int>(nombre, Allocator.Persistent);
            systemeMurs.Appuis = new NativeArray<int>(appuis.Count > 0 ? appuis.ToArray() : new int[1], Allocator.Persistent);
            systemeMurs.AiresAppuis = new NativeArray<float>(aires.Count > 0 ? aires.ToArray() : new float[1], Allocator.Persistent);
            systemeMurs.Aires = new NativeArray<float>(aire, Allocator.Persistent);
            systemeMurs.Poussees = new NativeArray<float3>(nb, Allocator.Persistent);
            systemeMurs.Etats = new NativeArray<byte>(nb, Allocator.Persistent);
            systemeMurs.AuMur = nb;
            systemeMurs.Chocs = !sansChocs;

            // Les pierres, dessinées par Entities Graphics : un cube unité, étiré à la taille de chacune.
            var desc = new RenderMeshDescription(ShadowCastingMode.On, receiveShadows: true);
            var proto = em.CreateEntity();
            RenderMeshUtility.AddComponents(proto, em, desc, new RenderMeshArray(materiauxMur, new[] { Boite(1, 1, 1, -0.5f) }), MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(proto, LocalTransform.Identity);
            em.AddComponentData(proto, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(proto, new PostTransformMatrix { Value = float4x4.identity });
            em.AddComponentData(proto, new Pierre());
            var pierres = em.Instantiate(proto, nb, Allocator.Temp);
            for (int i = 0; i < nb; i++)
            {
                em.SetComponentData(pierres[i], new Pierre { Index = i });
                em.SetComponentData(pierres[i], MaterialMeshInfo.FromRenderMeshArrayIndices(mats[i], 0));
                em.SetComponentData(pierres[i], LocalTransform.FromPositionRotation(centres[i], rots[i]));
                em.SetComponentData(pierres[i], new PostTransformMatrix { Value = float4x4.Scale(tailles[i]) });
            }
            pierres.Dispose();
            em.DestroyEntity(proto);
            eclats = gameObject.AddComponent<Eclats>();
            eclats.Preparer(materiauxMur[Basalte], materiauPoussiere, Boite(1, 1, 1, -0.5f));

            // Le réservoir de boulets.
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            var sphere = go.GetComponent<MeshFilter>().sharedMesh;
            Destroy(go);
            var protoB = em.CreateEntity();
            RenderMeshUtility.AddComponents(protoB, em, desc, new RenderMeshArray(new[] { materiauPierre }, new[] { sphere }), MaterialMeshInfo.FromRenderMeshArrayIndices(0, 0));
            em.AddComponentData(protoB, LocalTransform.FromPositionRotationScale(new float3(0, -100, 0), quaternion.identity, 0));
            em.AddComponentData(protoB, new LocalToWorld { Value = float4x4.identity });
            em.AddComponentData(protoB, new Boulet());
            var bs = em.Instantiate(protoB, 64, Allocator.Temp);
            boulets.AddRange(bs);
            bs.Dispose();
            em.DestroyEntity(protoB);

            // La fenêtre de la grille que les pans et leurs gravats peuvent changer.
            const float Marge = 25f;
            fenetreMurs = new RectInt(Mathf.FloorToInt(xmin - Marge - origineCases.x), Mathf.FloorToInt(zmin - Marge - origineCases.y),
                                      Mathf.CeilToInt(xmax - xmin + 2 * Marge), Mathf.CeilToInt(zmax - zmin + 2 * Marge));
            fenetreMurs.SetMinMax(Vector2Int.Max(fenetreMurs.min, Vector2Int.zero), Vector2Int.Min(fenetreMurs.max, new Vector2Int(cote, cote)));
            ActualiserMurs();
        }

        // Tirer un boulet : on prend le suivant du réservoir.
        public void Tirer(Vector3 depart, Vector3 v0, float masse, float rayon)
        {
            if (boulets.Count == 0) return;
            var e = boulets[prochainBoulet++ % boulets.Count];
            Em.SetComponentData(e, new Boulet { P = depart, V = v0, Masse = masse, Rayon = rayon, Etat = 1 });
            if (systemeMurs != null) systemeMurs.Tires++;
        }

        // Une pierre tombée se couche dans les gravats : son volume (foisonné d'un tiers) relève le sol
        // aux quatre points du relief qui l'entourent.
        public void Deposer(float3 p, float volume)
        {
            float pas = taille / (resolution - 1);
            float2 uv = (p.xz - origineRelief.xz) / pas;
            int2 i = (int2)math.floor(uv);
            if (i.x < 0 || i.y < 0 || i.x >= resolution - 1 || i.y >= resolution - 1) return;
            float2 f = uv - i;
            float dh = volume * 1.3f / (pas * pas);
            if (gravats == null) gravats = new float[hauteurs.Length];
            void Ajouter(int k, float v) { hauteurs[k] += v; gravats[k] += v; }
            Ajouter(i.y * resolution + i.x, dh * (1 - f.x) * (1 - f.y));
            Ajouter(i.y * resolution + i.x + 1, dh * f.x * (1 - f.y));
            Ajouter((i.y + 1) * resolution + i.x, dh * (1 - f.x) * f.y);
            Ajouter((i.y + 1) * resolution + i.x + 1, dh * f.x * f.y);
            Ebouler(i, pas);
            reliefChange = true;
        }

        // Les gravats s'éboulent jusqu'à leur pente naturelle (35°). La surface sur laquelle on marche est faite
        // de triangles, ceux que suit Sol.Hauteur : tant qu'un triangle est plus raide que cette pente, son sommet
        // le plus haut glisse de ses pierres vers le plus bas. Juger chaque sommet contre ses seuls voisins sur les
        // axes de la grille ne suffit pas : un tas réglé ainsi garde des facettes à 45°. Seuls les gravats
        // bougent ; le terrain naturel reste en place.
        float[] gravats;
        const float PenteGravats = 0.7f;
        void Ebouler(int2 centre, float pas)
        {
            const int R = 8;
            int n = resolution;
            int x0 = math.max(0, centre.x - R), x1 = math.min(n - 2, centre.x + R);
            int y0 = math.max(0, centre.y - R), y1 = math.min(n - 2, centre.y + R);
            var t = new int[3];
            for (int passe = 0; passe < 80; passe++)
            {
                bool bouge = false;
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                    {
                        int a = y * n + x;
                        // Les deux triangles de la maille, coupée le long de la diagonale (x, y)–(x+1, y+1).
                        for (int k = 0; k < 2; k++)
                        {
                            t[0] = a; t[1] = k == 0 ? a + 1 : a + n; t[2] = a + n + 1;
                            float h0 = hauteurs[t[0]], h1 = hauteurs[t[1]], h2 = hauteurs[t[2]];
                            float2 g = k == 0 ? new float2(h1 - h0, h2 - h1) : new float2(h2 - h1, h1 - h0);
                            float pente = math.length(g) / pas;
                            if (pente <= PenteGravats + 1e-3f) continue;
                            int haut = 0, bas = 0;
                            for (int j = 1; j < 3; j++)
                            {
                                if (hauteurs[t[j]] > hauteurs[t[haut]]) haut = j;
                                if (hauteurs[t[j]] < hauteurs[t[bas]]) bas = j;
                            }
                            int hi = t[haut], lo = t[bas];
                            if (gravats[hi] <= 1e-4f) continue;   // la raideur est celle du terrain naturel
                            float m = math.min(gravats[hi], 0.5f * (hauteurs[hi] - hauteurs[lo]) * (1f - PenteGravats / pente));
                            if (m <= 1e-4f) continue;
                            hauteurs[hi] -= m; gravats[hi] -= m;
                            hauteurs[lo] += m; gravats[lo] += m;
                            bouge = true;
                        }
                    }
                if (!bouge) break;
            }
        }

        // Fermer la porte : ses vantaux barrent le passage.
        public void FermerPorte()
        {
            if (carte == null || PorteFermee) return;
            PorteFermee = true;
            var tb = carte.porte;
            Tracer(statiques, cote, origineCases, new CarteDonnees.Bloc { nature = "vantaux", centre = tb.centre, demi = tb.demi, angle = tb.angle });
            var vantaux = GameObject.CreatePrimitive(PrimitiveType.Cube);
            vantaux.name = "Vantaux";
            Destroy(vantaux.GetComponent<Collider>());
            vantaux.transform.SetPositionAndRotation(new Vector3(tb.centre.x, tb.hauteur + 2.6f, tb.centre.y), Quaternion.identity);
            vantaux.transform.localScale = new Vector3(tb.demi.x * 2, 5.2f, 0.25f);
            var bois = Resources.FindObjectsOfTypeAll<Material>().FirstOrDefault(m => m.name == "bois_noir");
            if (bois) vantaux.GetComponent<MeshRenderer>().sharedMaterial = bois;
            var f = new RectInt(Mathf.FloorToInt(tb.centre.x - 10 - origineCases.x), Mathf.FloorToInt(tb.centre.y - 10 - origineCases.y), 20, 20);
            Actualiser(f);
        }

        void Update()
        {
            if (!Pret || systemeMurs == null || !systemeMurs.Pret) return;
            prochaineActualisation -= Time.deltaTime;
            if (prochaineActualisation > 0 || !(systemeMurs.Change || reliefChange)) return;
            prochaineActualisation = 1f;
            ActualiserMurs();
        }

        // Les pierres encore en place barrent le passage là où elles occupent la hauteur d'un homme au-dessus du sol
        // (gravats compris) ; le reste de la fenêtre suit le relief nouveau.
        void ActualiserMurs()
        {
            systemeMurs.Change = false;
            // Le relief d'abord : les gravats relèvent le sol sur lequel on juge les pierres encore debout.
            if (reliefChange) NouveauRelief(fenetreMurs);
            var em = Em;
            em.CompleteAllTrackedJobs();
            var f = fenetreMurs;
            for (int y = f.yMin; y < f.yMax; y++) for (int x = f.xMin; x < f.xMax; x++) murs[y * cote + x] = 0;
            if (!sansMurs)
            {
                var etats = systemeMurs.Etats;
                for (int i = 0; i < etats.Length; i++)
                {
                    if (etats[i] != 0) continue;
                    float3 c = systemeMurs.Centres[i], t = systemeMurs.Tailles[i];
                    float3 axe = math.mul(systemeMurs.Orientations[i], new float3(1, 0, 0));
                    float sol = hauteurs.Length > 0 ? Sol.Hauteur(ref relief.Value, c.xz) : 0;
                    if (c.y - t.y / 2 > sol + Passage || c.y + t.y / 2 < sol + 0.3f) continue;
                    // Une pierre barre toute case qu'elle touche, pas seulement celles dont elle couvre le centre :
                    // plus étroite qu'une case, elle n'en couvrirait parfois aucun, et l'on passerait au travers.
                    // On l'élargit donc d'une demi-case de chaque côté avant de tester les centres.
                    Tracer(murs, cote, origineCases, new CarteDonnees.Bloc { centre = new Vector2(c.x, c.z), demi = new Vector2(t.x / 2 + 0.5f, t.z / 2 + 0.5f), angle = math.atan2(axe.z, axe.x) });
                }
            }
            Actualiser(f);
        }

        // Le relief, avec ses gravats, remplace l'ancien ; les pentes de la fenêtre sont recalculées.
        void NouveauRelief(RectInt f)
        {
            var em = Em;
            em.CompleteAllTrackedJobs();
            reliefChange = false;
            var ancien = relief;
            relief = CreerRelief();
            em.SetComponentData(reliefEntite, new Relief { Blob = relief });
            ancien.Dispose();
            Pentes(f.xMin, f.yMin, f.width, f.height);
        }

        // Recompose la grille dans une fenêtre (pentes, emprises, pierres), puis la simulation et le planificateur.
        void Actualiser(RectInt f)
        {
            var em = Em;
            em.CompleteAllTrackedJobs();
            for (int y = f.yMin; y < f.yMax; y++)
                for (int x = f.xMin; x < f.xMax; x++)
                {
                    int i = y * cote + x;
                    cases[i] = (byte)(pentes[i] | statiques[i] | murs[i]);
                }
            var ancienO = obstacles;
            obstacles = CreerObstacles();
            em.SetComponentData(obstaclesEntite, new Obstacles { Blob = obstacles });
            ancienO.Dispose();
            Planificateur.Actualiser(cases, f.xMin, f.yMin, f.xMax, f.yMax);
        }

        // Pour les diagnostics des essais : ce qui barre une case (1 la pente, 2 une emprise ou la porte,
        // 4 une pierre en place), le sol du moment et l'épaisseur de gravats sous un point.
        public int Couches(float2 p)
        {
            int2 c = (int2)math.floor(p - origineCases);
            if (c.x < 0 || c.y < 0 || c.x >= cote || c.y >= cote) return 0;
            int i = c.y * cote + c.x;
            return pentes[i] | statiques[i] << 1 | murs[i] << 2;
        }
        public float SolEn(float2 p) => Sol.Hauteur(ref relief.Value, p);
        public float GravatsEn(float2 p)
        {
            if (gravats == null) return 0;
            float pas = taille / (resolution - 1);
            int2 i = math.clamp((int2)math.round((p - origineRelief.xz) / pas), 0, resolution - 1);
            return gravats[i.y * resolution + i.x];
        }

        void OnDestroy()
        {
            if (World.DefaultGameObjectInjectionWorld == null || !World.DefaultGameObjectInjectionWorld.IsCreated) return;
            Em.CompleteAllTrackedJobs();
            if (relief.IsCreated) relief.Dispose();
            if (obstacles.IsCreated) obstacles.Dispose();
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
                r.Chemin = 0;
                Tracer(e, ref r);
                Em.SetComponentData(e, r);
                liste.Add(e);
            }
            Rangs.Reclasser(Em, liste);
        }

        // Si la ligne droite est barrée (un mur, une maison, un ravin, un passage trop étroit pour le front),
        // le régiment prend la route que trouve le planificateur, en colonne aussi large que le plus étroit
        // de ses passages ; il reprendra son front à l'arrivée. S'il n'y a pas de route, il va tout droit.
        void Tracer(Entity e, ref Regiment r)
        {
            var route = Em.GetBuffer<PointChemin>(e);
            route.Clear();
            if (Planificateur == null) return;
            Vector2 depart = new Vector2(r.Position.x, r.Position.y), arrivee = new Vector2(r.Cible.x, r.Cible.y);
            if (Vector2.Distance(depart, arrivee) < 5f) return;
            float corps = 0.4f, marge = 0.5f;   // un demi-corps, et la demi-case de la grille
            if (Planificateur.Voit(depart, arrivee, r.Largeur * 0.5f + corps + marge)) return;
            // Un régiment ne s'engage que là où passe une colonne de trois files.
            var brut = Planificateur.Chercher(depart, arrivee, corps + marge + r.Espacement, out float etroit);
            if (brut == null) return;
            int files = math.clamp((int)math.floor(2f * (etroit - corps - marge) / r.Espacement) + 1, 1, r.Files);
            var points = Planificateur.Tendre(brut, (files - 1) * r.Espacement * 0.5f + corps + marge);
            route = Em.GetBuffer<PointChemin>(e);
            float s = 0;
            for (int k = 0; k < points.Count; k++)
            {
                if (k > 0) s += Vector2.Distance(points[k - 1], points[k]);
                route.Add(new PointChemin { P = points[k], S = s });
            }
            r.FilesOrdonnees = r.Files;
            r.Files = files;
            r.Chemin = 1;
            r.Abscisse = -r.Profondeur * 0.5f;   // la tête de la colonne au départ
            r.LongueurChemin = s;
            r.Front = math.normalizesafe((float2)(points[1] - points[0]), r.Front);
        }

        // Attaquer : chaque régiment prend l'ancre de l'ennemi pour cible et y pousse ses hommes.
        public void Attaquer(System.Collections.Generic.IEnumerable<Entity> regiments, Entity ennemi)
        {
            foreach (var e in regiments)
            {
                var r = Em.GetComponentData<Regiment>(e);
                r.Ennemi = ennemi;
                r.Chemin = 0;   // l'attaque va droit à l'ennemi
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
            r.Files = math.clamp(files, 1, math.max(1, r.Effectif)); r.Ordonne = 1; r.Ennemi = Entity.Null; r.Chemin = 0;
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
