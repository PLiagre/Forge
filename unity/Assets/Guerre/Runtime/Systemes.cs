using System.Collections.Generic;
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
    // Un régiment qui a ordre d'attaquer prend pour cible l'ancre de l'ennemi : ses
    // places passent dans les rangs adverses, et ses hommes poussent pour les atteindre.
    // Tant que le joueur n'a pas pris la main, un régiment marche entre ses deux lignes
    // et charge l'ennemi le plus proche qui passe à portée.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemeRegiments : ISystem
    {
        const float Halte = 8f;             // secondes d'arrêt sur chaque ligne
        const float VitesseAile = 1.6f;     // m/s : l'allure que les hommes de l'aile tiennent en pivot
        const float MarcheLongue = 30f;     // au-delà, le régiment se tourne vers sa marche ; en deçà, il garde son front
        const float VitesseCharge = 1.9f;   // m/s : le pas de charge
        const float Vue = 150f;             // m : distance à laquelle le scénario de démonstration charge
        const float Abord = 7f;             // m entre les fronts où l'on serre les rangs avant le choc
        const float Enfoncement = 2f;       // m : l'attaque vise à enfoncer le front ennemi d'autant
        const float CorpsEpaisseur = 0.8f;  // m entre les centres de deux hommes qui se touchent
        const float Trot = 3.5f, Galop = 7.5f;   // m/s : l'approche de la cavalerie, puis sa charge
        const float DistanceGalop = 110f;   // m : on prend le galop pour la dernière centaine de mètres
        const float Traverser = 8f;         // m : la charge vise au-delà du dernier rang ennemi
        const float Alerte = 70f;           // m : un ennemi de front à cette distance, les piques s'abaissent
        const float ChargeEpuisee = 1.5f;   // m/s : au contact et plus lente que cela, la charge est finie

        EntityQuery tous;

        public void OnCreate(ref SystemState state)
        {
            tous = SystemAPI.QueryBuilder().WithAllRW<Regiment>().Build();
            state.RequireForUpdate<Regiment>();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            float dt = SystemAPI.Time.DeltaTime;
            var ents = tous.ToEntityArray(Allocator.Temp);
            var regs = tous.ToComponentDataArray<Regiment>(Allocator.Temp);
            var avant = new NativeArray<float2>(regs.Length, Allocator.Temp);
            for (int i = 0; i < regs.Length; i++) avant[i] = regs[i].Position;
            for (int i = 0; i < regs.Length; i++)
            {
                var r = regs[i];
                r.Melee = r.Contacts > 0 ? 2f : math.max(0, r.Melee - dt);
                r.Tir = 0;
                // Un ennemi approche de front : l'officier fait baisser les piques. Ce n'est pas une
                // protection : c'est un ordre, et seuls les hommes arrêtés, piques basses, arrêtent un cheval.
                r.Herisse = 0;
                if (r.Arme == 0 && r.Deroute == 0)
                    for (int j = 0; j < regs.Length; j++)
                    {
                        if (regs[j].Camp == r.Camp || regs[j].Effectif <= 0) continue;
                        // On voit venir des hommes, pas une ancre : c'est là où ils sont qui compte.
                        float2 vers = regs[j].CentreHommes - r.Position;
                        float d = math.length(vers);
                        if (d < Alerte + (r.Profondeur + regs[j].Profondeur) * 0.5f && math.dot(vers, r.Front) > 0.5f * d) { r.Herisse = 1; break; }
                    }
                if (r.Effectif <= 0) { r.Ennemi = Entity.Null; regs[i] = r; continue; }
                // La déroute n'est pas un ordre : c'est la moitié des hommes qui fuient. Le régiment
                // cesse alors d'attaquer et se regroupe là où restent ceux qui tiennent ; il se
                // rallie quand ses fuyards reviennent.
                if (r.Deroute == 0 && r.Fuyards >= 0.5f) { r.Deroute = 1; r.Ennemi = Entity.Null; }
                else if (r.Deroute != 0 && r.Fuyards < 0.2f) r.Deroute = 0;
                if (r.Deroute != 0)
                {
                    r.Position += (r.CentreHommes - r.Position) * math.saturate(dt * 2f);
                    r.Cible = r.Position;
                    regs[i] = r;
                    continue;
                }

                // Le scénario de démonstration charge l'ennemi le plus proche.
                if (r.Ordonne == 0 && r.Ennemi == Entity.Null)
                {
                    float meilleur = Vue;
                    for (int j = 0; j < regs.Length; j++)
                    {
                        if (regs[j].Camp == r.Camp || regs[j].Effectif <= 0) continue;
                        float d = math.distance(regs[j].Position, r.Position);
                        if (d < meilleur) { meilleur = d; r.Ennemi = ents[j]; }
                    }
                }
                float vitesse = r.VitesseMarche;
                if (r.Ennemi != Entity.Null)
                {
                    int j = ents.IndexOf(r.Ennemi);
                    if (j < 0 || regs[j].Effectif <= 0) { r.Ennemi = Entity.Null; r.Cible = r.Position; }
                    else if (r.Arme == 2 && r.Contacts == 0 && math.length(regs[j].Position - r.Position) > (r.Profondeur + regs[j].Profondeur) * 0.5f + Abord)
                    {
                        // Des arbalétriers ne chargent pas : ils s'approchent à portée, s'arrêtent et tirent.
                        // Si l'ennemi vient au contact, ils se défendent à la dague comme les autres.
                        float2 vers = regs[j].Position - r.Position;
                        float d = math.length(vers);
                        r.FrontCible = math.normalizesafe(vers, r.Front);
                        if (d > Armes.PorteeTir) r.Cible = regs[j].Position - r.FrontCible * (Armes.PorteeTir - 15f);
                        else
                        {
                            if (math.distance(r.Cible, r.Position) > 1f && math.dot(r.Cible - r.Position, r.FrontCible) > 0) r.Cible = r.Position;
                            r.Tir = 1;
                        }
                    }
                    else if (Corps.Monte(r.Arme))
                    {
                        // La cavalerie ne serre pas les rangs pour pousser : elle prend le trot, puis le galop
                        // pour la dernière centaine de mètres, et vise au-delà de l'ennemi. Ce qui l'arrête, ce
                        // sont les corps et les fers qu'elle rencontre ; au contact, l'ancre suit ses hommes.
                        float2 vers = regs[j].Position - r.Position;
                        float d = math.length(vers);
                        float2 dirE = r.Contacts > 0 ? r.FrontCible : math.normalizesafe(vers, r.Front);
                        r.FrontCible = dirE;
                        r.Cible = r.Position + dirE * (math.dot(vers, dirE) + regs[j].Profondeur * 0.5f + Traverser);
                        vitesse = d - regs[j].Profondeur * 0.5f > DistanceGalop ? Trot : Galop;
                        // Une charge arrêtée a perdu son élan : les cavaliers se battent là où ils sont, sans
                        // se jeter de nouveau, au pas, sur ce qui les a arrêtés. Ils rechargeront une fois dégagés.
                        if (r.Contacts > 0 && math.length(r.Vitesse) < ChargeEpuisee) r.Cible = r.Position;
                    }
                    else
                    {
                        float2 vers = regs[j].Position - r.Position;
                        // Engagé, on garde son axe d'attaque : viser l'ancre ennemie à chaque pas ferait
                        // tourner les deux blocs l'un autour de l'autre au moindre décalage.
                        float2 dirE = r.Melee > 0 ? r.FrontCible : math.normalizesafe(vers, r.Front);
                        r.FrontCible = dirE;
                        // L'ordre d'attaque : porter son front à Enfoncement mètres au-delà du front ennemi.
                        // Les deux premiers rangs se touchent quand les ancres sont à une demi-profondeur
                        // de chacun, plus l'épaisseur d'un corps.
                        float ecartVoulu = math.max(0f, (r.Profondeur + regs[j].Profondeur) * 0.5f + CorpsEpaisseur - Enfoncement);
                        r.Cible = r.Position + dirE * (math.dot(vers, dirE) - ecartVoulu);
                        vitesse = VitesseCharge;
                        // À quelques pas de l'ennemi, on serre les rangs et l'on avance au pas :
                        // les deux fronts se rencontrent en murs, pas en foules qui s'entremêlent.
                        float abord = (r.Profondeur + regs[j].Profondeur) * 0.5f + Abord;
                        if (math.length(vers) < abord) r.Melee = math.max(r.Melee, 2f);
                    }
                }

                // Un régiment est là où sont ses hommes : s'ils sont repoussés loin de leur place,
                // l'ancre les suit. Celui qui cède du terrain recule avec ses hommes.
                r.Position += (r.CentreHommes - r.Position) * math.saturate(dt * 0.8f * math.smoothstep(2f, 5f, r.Ecart));
                // Au contact, le régiment est là où se battent ses hommes : l'ancre les suit le long
                // de l'axe du combat, et n'avance plus d'elle-même : c'est la poussée des hommes qui la
                // déplace. Sur le côté, elle reste : les hommes reviennent à leurs files au lieu de glisser.
                // La cavalerie, elle, ne s'arrête pas d'elle-même au contact : ce sont les corps et les
                // fers qui l'arrêtent, et son ancre attend alors ses cavaliers (cohésion, plus bas).
                if (r.Contacts > 0 && r.Ennemi != Entity.Null && !Corps.Monte(r.Arme))
                {
                    r.Position += r.Front * math.dot(r.CentreHommes - r.Position, r.Front) * math.saturate(dt * 2f);
                    r.Cible = r.Position;
                }
                float2 v2 = r.Cible - r.Position;
                float dist = math.length(v2);
                // Le régiment attend ses hommes : si ceux-ci sont loin de leur place
                // (gênés, bousculés, arrêtés par l'ennemi), l'ordre ralentit avec eux.
                float cohesion = 1f - math.smoothstep(1.5f, 5f, r.Ecart);
                // Un front large pivote lentement : ses ailes doivent courir.
                float pivot = math.min(0.5f, VitesseAile / math.max(r.Largeur * 0.5f, 1f)) * math.max(cohesion, 0.15f) * dt;
                if (dist > 0.3f)
                {
                    float2 dir = v2 / dist;
                    bool longue = dist > MarcheLongue;
                    r.Front = Tourner(r.Front, longue ? dir : r.FrontCible, pivot);
                    // En marche longue, on n'avance vraiment qu'une fois tourné vers elle.
                    // En marche courte, les hommes se décalent ou reculent sans tourner le dos.
                    float allure = longue ? math.max(math.saturate(math.dot(r.Front, dir)), 0.25f) : 0.7f;
                    r.Position += dir * math.min(dist, vitesse * dt * allure * cohesion);
                }
                else
                {
                    r.Front = Tourner(r.Front, r.FrontCible, pivot);
                    if (r.Ordonne == 0 && r.Ennemi == Entity.Null)
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
                regs[i] = r;
            }
            // L'allure de chaque ligne : les cavaliers la tiennent, puis corrigent leur retard.
            for (int i = 0; i < regs.Length; i++) { var r = regs[i]; r.Vitesse = dt > 0 ? math.clamp((r.Position - avant[i]) / dt, -10f, 10f) : float2.zero; regs[i] = r; }
            tous.CopyFromComponentDataArray(regs);
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

    // Chaque soldat est un corps : 80 kg à pied, 620 kg pour un cheval et son cavalier. Il pousse
    // vers sa place avec une force qui faiblit à mesure qu'il prend de la vitesse, comme un muscle ;
    // les corps en contact se repoussent comme des ressorts. Une file qui pousse transmet donc
    // l'effort de chacun de ses hommes jusqu'au premier rang : dix rangs poussent plus
    // fort que cinq, sans qu'aucune règle ne le dise.
    // À portée d'un ennemi, il frappe à son rythme ; le coup porte d'autant plus
    // souvent que la cible est fatiguée ou écrasée par la presse, qui l'empêche de parer.
    // Un choc plus lourd que soi, trop brusque pour qu'on le suive d'un pas, renverse ; une
    // pique baissée est un ressort pointé devant le piquier, qui plie, blesse et se rompt.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemeRegiments))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemePilotage : ISystem
    {
        public const float Cellule = 1.2f;
        public const float CaseLongue = 4f;   // les grilles des piques et des chevaux : une pique porte à 3,2 m
        NativeParallelMultiHashMap<int, Voisin> grille;
        NativeQueue<Coup> coups;
        NativeParallelHashMap<int, float2> effroi;   // morts de l'image précédente, par case de 4 m et par camp
        NativeQueue<Tir> tirs;
        NativeParallelMultiHashMap<int, PavoisPlante> pavois;   // les pavois plantés, par case
        NativeParallelMultiHashMap<int, Pointe> piques;         // les piques baissées, par case de 4 m
        NativeParallelMultiHashMap<int, Cheval> chevaux;        // les chevaux, par case de 4 m
        NativeQueue<byte> evenements;                // 1 carreau arrêté par un pavois, 2 carreau au sol, 3 carreau tiré, 4 homme renversé, 5 pique rompue
        ComponentLookup<Regiment> regiments, regimentsRW;
        ComponentLookup<Soldat> soldatsRW;
        EntityQuery soldats;
        uint image;

        public void OnCreate(ref SystemState state)
        {
            grille = new NativeParallelMultiHashMap<int, Voisin>(16384, Allocator.Persistent);
            coups = new NativeQueue<Coup>(Allocator.Persistent);
            effroi = new NativeParallelHashMap<int, float2>(1024, Allocator.Persistent);
            tirs = new NativeQueue<Tir>(Allocator.Persistent);
            pavois = new NativeParallelMultiHashMap<int, PavoisPlante>(16384, Allocator.Persistent);
            piques = new NativeParallelMultiHashMap<int, Pointe>(16384, Allocator.Persistent);
            chevaux = new NativeParallelMultiHashMap<int, Cheval>(4096, Allocator.Persistent);
            evenements = new NativeQueue<byte>(Allocator.Persistent);
            regimentsRW = state.GetComponentLookup<Regiment>(false);
            regiments = state.GetComponentLookup<Regiment>(true);
            soldatsRW = state.GetComponentLookup<Soldat>(false);
            soldats = SystemAPI.QueryBuilder().WithAll<Soldat, LocalTransform>().Build();
            state.RequireForUpdate<Relief>();
            state.RequireForUpdate(soldats);
        }

        public void OnDestroy(ref SystemState state)
        {
            if (grille.IsCreated) grille.Dispose();
            if (coups.IsCreated) coups.Dispose();
            if (effroi.IsCreated) effroi.Dispose();
            if (tirs.IsCreated) tirs.Dispose();
            if (pavois.IsCreated) pavois.Dispose();
            if (piques.IsCreated) piques.Dispose();
            if (chevaux.IsCreated) chevaux.Dispose();
            if (evenements.IsCreated) evenements.Dispose();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            int n = soldats.CalculateEntityCount();
            if (grille.Capacity < n || piques.Capacity < n || chevaux.Capacity < n)
            {
                state.Dependency.Complete();
                if (grille.Capacity < n) grille.Capacity = n * 2;
                if (piques.Capacity < n) piques.Capacity = n * 2;
                if (chevaux.Capacity < n) chevaux.Capacity = n * 2;
            }
            regiments.Update(ref state);
            regimentsRW.Update(ref state);
            soldatsRW.Update(ref state);
            var relief = SystemAPI.GetSingleton<Relief>().Blob;
            // Le pas est fixe (Bataille.PasSimulation) ; la borne ne sert qu'en cas d'appel hors du pas fixe.
            float dt = math.min(SystemAPI.Time.DeltaTime, 1f / 30f);
            if (dt <= 0) return;
            var reglages = SystemAPI.TryGetSingleton<ReglagesSimulation>(out var rg) ? rg : new ReglagesSimulation { Corps = 1, Poussee = 1, Peur = 1, Pavois = 1, Masse = 1, Piques = 1 };
            var compte = SystemAPI.HasSingleton<CompteTir>() ? SystemAPI.GetSingletonEntity<CompteTir>() : Entity.Null;
            image++;

            var dep = new ViderGrille { Grille = grille, Piques = piques, Chevaux = chevaux }.Schedule(state.Dependency);
            dep = new ViderPavois { Pavois = pavois }.Schedule(dep);
            dep = new RemplirPavois { Plantes = pavois.AsParallelWriter() }.ScheduleParallel(dep);
            dep = new RemplirGrille
            {
                Grille = grille.AsParallelWriter(), Piques = piques.AsParallelWriter(), Chevaux = chevaux.AsParallelWriter(),
                Regiments = regiments, MasseChevaux = reglages.Masse, PiquesActives = reglages.Piques,
            }.ScheduleParallel(dep);
            dep = new Piloter
            {
                Grille = grille, Piques = piques, Chevaux = chevaux, Regiments = regiments, Relief = relief, Dt = dt, Corps = reglages.Corps,
                Poussee = reglages.Poussee, Peur = reglages.Peur, Pavois = reglages.Pavois, MasseChevaux = reglages.Masse, PiquesActives = reglages.Piques,
                Effroi = effroi, Coups = coups.AsParallelWriter(), Tirs = tirs.AsParallelWriter(), Evenements = evenements.AsParallelWriter(),
                Graine = image * 2654435761u,
            }.ScheduleParallel(dep);
            // Les carreaux en vol, puis ceux qu'on vient de tirer, puis les pavois qui suivent leurs porteurs.
            dep = new Voler { Grille = grille, Plantes = pavois, Relief = relief, Dt = dt, Coups = coups.AsParallelWriter(), Evenements = evenements.AsParallelWriter(), Graine = image * 40503u }.ScheduleParallel(dep);
            dep = new Lancer { Tirs = tirs, Evenements = evenements.AsParallelWriter() }.Schedule(dep);
            dep = new ViderTirs { Tirs = tirs }.Schedule(dep);
            // Les morts de cette image seront vus par leurs voisins à l'image suivante.
            dep = new Appliquer { Coups = coups, Soldats = soldatsRW, Regiments = regimentsRW, Effroi = effroi, Peur = reglages.Peur }.Schedule(dep);
            if (compte != Entity.Null)
                dep = new Compter { Evenements = evenements, Compte = SystemAPI.GetComponentLookup<CompteTir>(false), Entite = compte }.Schedule(dep);
            else dep = new ViderEvenements { Evenements = evenements }.Schedule(dep);
            state.Dependency = dep;
        }

        // Un homme campé (arrêté, à sa place) a ses appuis au sol : il cède moins
        // qu'un homme en marche quand un autre régiment ami le bouscule, et s'efface
        // devant un camarade qui rejoint sa place.
        public static float Appui(in Soldat s)
        {
            float campe = math.saturate(1f - math.length(s.Vitesse) / 0.8f) * (1f - math.smoothstep(0.5f, 1.5f, s.Ecart));
            return 1f + 3f * campe;
        }

        public static int Cle(int2 c) => (c.x * 73856093) ^ (c.y * 19349663);

        public struct Voisin
        {
            public float2 P, V;
            public Entity E;
            public int Regiment;
            public byte Camp, Arme, Fuite;
            public float Appui, Fatigue, Presse, Peur;
            public float2 Front;      // vers où il fait face : il ne pare que de ce côté
            public float2 Regard;     // vers où il regarde : son pavois, planté, est devant lui
            public byte Poste;        // 1 : son pavois est planté
            public float Taille;      // hauteur de son corps : moindre à genou, et à terre
            public float Masse, Rayon;
            public byte AuSol;        // 1 : renversé ; on l'enjambe, on le piétine
        }

        public struct PavoisPlante { public float3 Base; public float2 Normale; }

        // Une pique baissée : le piquier, l'axe de sa pique, et combien il est campé pour la tenir.
        public struct Pointe { public float2 Base, Axe, V; public float Appui; public byte Camp; }

        // Un cheval, pour les piquiers qui le reçoivent et les hommes à terre qu'il piétine.
        public struct Cheval { public float2 P, V; public float Rayon; public byte Camp; }

        // Où la pointe d'une pique entre dans un cheval : la pique est un segment qui part du piquier
        // et porte à Portee(0) ; le cheval, un disque. Renvoie l'enfoncement de la pointe, en mètres.
        public static float Enfoncement(float2 piquier, float2 axe, float2 cheval, float rayon)
        {
            float2 d = cheval - piquier;
            float long_ = math.dot(d, axe), lat = math.abs(math.dot(d, new float2(axe.y, -axe.x)));
            if (long_ < 0.3f || lat >= rayon) return 0f;
            float surface = long_ - math.sqrt(rayon * rayon - lat * lat);
            return math.max(0f, Armes.Portee(0) - surface);
        }

        // La force d'une pique enfoncée : un ressort amorti qui plie au-delà de ForcePique, et qui
        // ne porte plus rien une fois rompu.
        public static float ForcePique(float enfoncement, float rapprochement) =>
            enfoncement <= 0f || enfoncement > Armes.PiqueRompue ? 0f
            : math.min(Armes.RaideurPique * enfoncement + 4000f * math.max(0f, rapprochement), Armes.ForcePique);

        [BurstCompile]
        struct ViderPavois : IJob
        {
            public NativeParallelMultiHashMap<int, PavoisPlante> Pavois;
            public void Execute() => Pavois.Clear();
        }

        [BurstCompile]
        partial struct RemplirPavois : IJobEntity
        {
            public NativeParallelMultiHashMap<int, PavoisPlante>.ParallelWriter Plantes;
            void Execute(in Pavois p)
            {
                if (p.Plante == 0) return;
                Plantes.Add(Cle((int2)math.floor(p.Base.xz / Cellule)), new PavoisPlante { Base = p.Base, Normale = p.Normale });
            }
        }

        public const float CaseEffroi = 4f;
        public static int CleEffroi(float2 p) => Cle((int2)math.floor(p / CaseEffroi));

        [BurstCompile]
        struct ViderGrille : IJob
        {
            public NativeParallelMultiHashMap<int, Voisin> Grille;
            public NativeParallelMultiHashMap<int, Pointe> Piques;
            public NativeParallelMultiHashMap<int, Cheval> Chevaux;
            public void Execute() { Grille.Clear(); Piques.Clear(); Chevaux.Clear(); }
        }

        [BurstCompile]
        partial struct RemplirGrille : IJobEntity
        {
            public NativeParallelMultiHashMap<int, Voisin>.ParallelWriter Grille;
            public NativeParallelMultiHashMap<int, Pointe>.ParallelWriter Piques;
            public NativeParallelMultiHashMap<int, Cheval>.ParallelWriter Chevaux;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            public byte MasseChevaux, PiquesActives;
            void Execute(Entity e, in Soldat s, in LocalTransform t)
            {
                float2 p = t.Position.xz;
                bool monte = Corps.Monte(s.Arme);
                Grille.Add(Cle((int2)math.floor(p / Cellule)), new Voisin
                {
                    P = p, V = s.Vitesse, E = e, Regiment = s.Regiment.Index, Camp = s.Camp, Arme = s.Arme, Fuite = s.Fuite,
                    Appui = Appui(s), Fatigue = s.Fatigue, Presse = s.Presse, Peur = s.Peur, Front = Regiments[s.Regiment].Front,
                    Regard = s.Regard, Poste = s.Poste, Taille = s.AuSol > 0 ? 0.4f : monte ? Corps.Taille(s.Arme) : math.lerp(1.75f, 1.2f, s.Abri),
                    Masse = Corps.Masse(s.Arme, MasseChevaux), Rayon = Corps.Rayon(s.Arme), AuSol = (byte)(s.AuSol > 0 ? 1 : 0),
                });
                int2 cl = (int2)math.floor(p / CaseLongue);
                if (monte) Chevaux.Add(Cle(cl), new Cheval { P = p, V = s.Vitesse, Rayon = Corps.Rayon(s.Arme), Camp = s.Camp });
                // Une pique ne compte que baissée, tenue par un homme debout qui ne fuit pas.
                else if (PiquesActives != 0 && s.Arme == 0 && s.Garde > 0.7f && s.Fuite == 0 && s.AuSol <= 0 && s.Brisee == 0)
                    Piques.Add(Cle(cl), new Pointe
                    {
                        Base = p, Axe = s.Regard, V = s.Vitesse, Camp = s.Camp,
                        // Arrêté, on plante le talon de la pique en terre et l'on s'arc-boute : en marche, on ne le peut pas.
                        Appui = math.saturate(1f - math.length(s.Vitesse) / 0.6f),
                    });
            }
        }

        [BurstCompile]
        partial struct Piloter : IJobEntity
        {
            [ReadOnly] public NativeParallelMultiHashMap<int, Voisin> Grille;
            [ReadOnly] public NativeParallelMultiHashMap<int, Pointe> Piques;
            [ReadOnly] public NativeParallelMultiHashMap<int, Cheval> Chevaux;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            [ReadOnly] public NativeParallelHashMap<int, float2> Effroi;
            public NativeQueue<Coup>.ParallelWriter Coups;
            public NativeQueue<Tir>.ParallelWriter Tirs;
            public NativeQueue<byte>.ParallelWriter Evenements;
            public float Dt;
            public byte Corps, Poussee, Peur, Pavois, MasseChevaux, PiquesActives;
            public uint Graine;

            const float Raideur = 80000f;     // N/m : un corps, une armure, un bouclier écrasés
            const float Amorti = 2400f;       // N·s/m : les corps ne rebondissent pas
            const float Frottement = 0.8f;    // coefficient entre deux corps : armures, boucliers, mains qui agrippent
            const float Glissement = 3000f;   // N·s/m : régularise le frottement à faible vitesse
            const float Marge = 0.05f;        // m : l'espace personnel face aux autres régiments amis
            const float Ecrasement = 0.5625f; // part du contact en deçà de laquelle même la presse ne peut plus écraser deux corps
            const float VitessePresse = 0.5f; // m/s : dans la presse, on avance pas à pas
            const float Foulee = 1.5f;        // m parcourus par cycle de marche cuit (deux pas)
            const float Vue = 3.6f;           // m : ce qu'un homme perçoit autour de lui dans la mêlée
            // On suit d'un pas une poussée jusqu'à 45 m/s² : au-delà, un choc plus lourd que soi renverse.
            const float Renversement = 45f;
            const float Trebucher = 700f;     // N : ce que coûte à un cheval chaque corps à terre sous ses sabots

            // Un corps touche devant soi (à un cône de 50° près) : c'est sur lui qu'on appuie.
            bool QuelquUnDevant(Entity e, float2 pos, float2 front, float rayon)
            {
                int2 c = (int2)math.floor(pos / Cellule);
                for (int dz = -1; dz <= 1; dz++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                    do
                    {
                        if (q.E == e || q.AuSol != 0) continue;
                        float2 d = q.P - pos;
                        float l = math.length(d);
                        if (l < rayon + q.Rayon + 0.1f && math.dot(d, front) > 0.64f * l) return true;
                    } while (Grille.TryGetNextValue(out q, ref it));
                }
                return false;
            }

            void Execute(Entity e, ref Soldat s, ref LocalTransform t, ref AnimEtat anim, ref AnimCombat combat)
            {
                var r = Regiments[s.Regiment];
                bool monte = global::Guerre.Corps.Monte(s.Arme);
                // Des chevaux ne se serrent pas en presse : ils chargent, et ce qui les arrête, ce sont les corps.
                bool melee = r.Melee > 0 && !monte;
                float2 front = r.Front;
                float2 pos0 = t.Position.xz;
                float masse = global::Guerre.Corps.Masse(s.Arme, MasseChevaux), rayon = global::Guerre.Corps.Rayon(s.Arme);
                var alea0 = Random.CreateFromIndex((uint)e.Index * 104729u + Graine);

                // Renversé : il reste à terre, glisse sur son élan, et se relève quand il le peut.
                if (s.AuSol > 0)
                {
                    s.AuSol -= Dt;
                    // Un cheval lancé qui passe sur un homme à terre le piétine.
                    float pietine = 0f;
                    int2 ch = (int2)math.floor(pos0 / CaseLongue);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Chevaux.TryGetFirstValue(Cle(ch + new int2(dx, dz)), out var h, out var ith)) continue;
                        do
                        {
                            float vh = math.length(h.V);
                            if (vh > 1.5f && math.distance(h.P, pos0) < h.Rayon + 0.3f) pietine += 0.08f * vh * Dt;
                        } while (Chevaux.TryGetNextValue(out h, ref ith));
                    }
                    if (pietine > 0) Coups.Enqueue(new Coup { Cible = e, Degats = pietine, Lieu = pos0, Camp = s.Camp });
                    s.Vitesse *= math.saturate(1f - 4f * Dt);
                    float2 p = pos0 + s.Vitesse * Dt;
                    s.Contact = 0; s.APortee = 0; s.Presse = 0; s.Poste = 0; s.Garde = 0; s.Abri = 0;
                    s.Recharge = math.max(s.Recharge, 0.8f);
                    if (s.AuSol <= 0) s.AuSol = 0;
                    anim.Value = new float4(s.Phase, 0, 0, -1);
                    combat.Value = float4.zero;
                    // Il tombe à la renverse ; en se relevant, il reprend la verticale (plus bas).
                    var couche = math.mul(quaternion.LookRotationSafe(new float3(s.Regard.x, 0, s.Regard.y), math.up()), quaternion.RotateX(-math.PI / 2));
                    t.Rotation = math.slerp(t.Rotation, couche, math.saturate(Dt * 12f));
                    t.Position = new float3(p.x, Sol.Hauteur(ref Relief.Value, p) + 0.12f, p.y);
                    s.Lieu = t.Position;
                    s.Ecart = math.distance(p, Formation.VersMonde(Formation.Place(r, s.Numero) + s.Decalage, r.Position, front));
                    return;
                }

                // Ce qu'il voit autour de lui : l'ennemi à portée devant lui, la menace, ses camarades
                // et leur peur. Rien de cela n'est un modificateur : ce sont des perceptions.
                bool trouve = false; Voisin cible = default;
                float2 menace = float2.zero; int ennemisProches = 0, camaradesProches = 0, ennemisHorsDeVue = 0;
                float peurVoisins = 0; int nPeur = 0;
                float devantX = 1e9f, devantSol = 0f;   // le camarade le plus proche sur sa ligne de tir
                if (melee || r.Ennemi != Entity.Null || s.Fuite != 0 || s.Peur > 0.02f)
                {
                    float portee = Armes.Portee(s.Arme), meilleur = portee * portee;
                    int rc = (int)math.ceil(math.max(portee, Vue) / Cellule);
                    int2 cc = (int2)math.floor(pos0 / Cellule);
                    for (int dz = -rc; dz <= rc; dz++)
                    for (int dx = -rc; dx <= rc; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(cc + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.E == e) continue;
                            float2 d = q.P - pos0;
                            float l2 = math.lengthsq(d);
                            if (q.Camp == s.Camp)
                            {
                                float x = math.dot(d, front), cote = math.dot(d, new float2(front.y, -front.x));
                                if (x > 0.2f && x < devantX && math.abs(cote) < 0.35f) { devantX = x; devantSol = Sol.Hauteur(ref Relief.Value, q.P); }
                                if (l2 < 1.5f * 1.5f && q.Fuite == 0 && q.AuSol == 0) camaradesProches++;
                                if (l2 < 2.4f * 2.4f) { peurVoisins += q.Peur; nPeur++; }
                                continue;
                            }
                            if (l2 < Vue * Vue && q.Fuite == 0 && q.AuSol == 0)
                            {
                                ennemisProches++; menace -= d / math.max(l2, 0.25f);
                                // Un ennemi à côté de soi ou dans le dos : on ne peut ni le parer ni le frapper.
                                if (math.dot(d, front) < 0f) ennemisHorsDeVue++;
                            }
                            // On ne frappe que devant soi : l'ennemi qui vient de côté, on ne peut pas lui répondre.
                            if (s.Fuite == 0 && l2 < meilleur && math.dot(d, front) > 0.25f * math.sqrt(l2)) { meilleur = l2; cible = q; trouve = true; }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                }

                // Les piques. Un cheval sent les fers pointés devant lui, et ceux qui entrent dans son
                // poitrail le freinent et le blessent ; un piquier reçoit dans sa pique le cheval qui s'y jette.
                float2 forcePiques = float2.zero, choc = float2.zero, elan = float2.zero;
                float renverse = 0f;
                int pointesDevant = 0;
                float energie = 0f;
                if (monte)
                {
                    int2 cp = (int2)math.floor(pos0 / CaseLongue);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Piques.TryGetFirstValue(Cle(cp + new int2(dx, dz)), out var pk, out var itp)) continue;
                        do
                        {
                            if (pk.Camp == s.Camp) continue;
                            float2 d = pos0 - pk.Base;
                            float long_ = math.dot(d, pk.Axe), lat = math.abs(math.dot(d, new float2(pk.Axe.y, -pk.Axe.x)));
                            // Des fers pointés vers soi, à quelques pas : le cheval les voit.
                            if (long_ > 0f && long_ < Armes.Portee(0) + 4f && lat < 1.2f && math.dot(s.Vitesse, pk.Axe) < 0.5f) pointesDevant++;
                            float enf = Enfoncement(pk.Base, pk.Axe, pos0, rayon);
                            float rapproche = -math.dot(s.Vitesse - pk.V, pk.Axe);
                            float f = ForcePique(enf, rapproche);
                            if (f <= 0f) continue;
                            forcePiques += pk.Axe * f;
                            energie += f * math.max(0f, rapproche) * Dt;
                        } while (Piques.TryGetNextValue(out pk, ref itp));
                    }
                    if (energie > 0f)
                        Coups.Enqueue(new Coup { Cible = e, Degats = energie / Armes.EnergieMortelle, Lieu = pos0, Camp = s.Camp });
                }
                else if (PiquesActives != 0 && s.Arme == 0 && s.Garde > 0.7f && s.Fuite == 0 && s.Brisee == 0)
                {
                    float appui = math.saturate(1f - math.length(s.Vitesse) / 0.6f);
                    int2 cp = (int2)math.floor(pos0 / CaseLongue);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Chevaux.TryGetFirstValue(Cle(cp + new int2(dx, dz)), out var h, out var ith)) continue;
                        do
                        {
                            if (h.Camp == s.Camp) continue;
                            float enf = Enfoncement(pos0, s.Regard, h.P, h.Rayon);
                            if (enf > Armes.PiqueRompue) { s.Brisee = 1; Evenements.Enqueue(5); break; }
                            float f = ForcePique(enf, -math.dot(h.V - s.Vitesse, s.Regard));
                            // Le talon planté en terre porte l'essentiel du choc ; en marche, c'est l'homme qui le reçoit.
                            if (f > 0f) { float2 recu = -s.Regard * f * (1f - 0.85f * appui); forcePiques += recu; choc += recu; }
                        } while (Chevaux.TryGetNextValue(out h, ref ith));
                    }
                }

                // La peur.
                if (Peur != 0)
                {
                    float2 morts = float2.zero;
                    int2 ce = (int2)math.floor(pos0 / CaseEffroi);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                        if (Effroi.TryGetValue(Cle(ce + new int2(dx, dz)), out var m)) morts += m;
                    float amis = s.Camp == 0 ? morts.x : morts.y, ennemis = s.Camp == 0 ? morts.y : morts.x;
                    float amplification = 1f + s.Fatigue;
                    // Un camarade qui tombe à côté de soi ; un ennemi qui tombe rassure un peu.
                    float effroiGain = (0.10f * amis - 0.02f * ennemis) * amplification;
                    // Seul, ou presque, avec l'ennemi tout près.
                    if (ennemisProches > 0 && camaradesProches < 2) effroiGain += 0.06f * Dt * amplification;
                    // L'ennemi qu'on ne peut pas affronter, sur le côté ou derrière soi.
                    effroiGain += 0.07f * math.min(ennemisHorsDeVue, 3) * Dt * amplification;
                    // Un cheval ne se jette pas de lui-même sur des fers qu'il voit : il renâcle.
                    effroiGain += 0.05f * math.min(pointesDevant, 6) * Dt * amplification;
                    s.Peur += effroiGain;
                    // La panique gagne vite ses voisins ; le calme, lentement.
                    if (nPeur > 0)
                    {
                        float moyenne = peurVoisins / nPeur;
                        s.Peur += (moyenne - s.Peur) * (moyenne > s.Peur ? 0.8f * amplification : 0.15f) * Dt;
                    }
                    // Elle retombe d'elle-même, plus vite loin de l'ennemi et entouré des siens.
                    s.Peur -= Dt * (0.015f + (ennemisProches == 0 ? 0.04f : 0f) + 0.01f * math.min(camaradesProches, 4));
                    s.Peur = math.saturate(s.Peur);
                    if (s.Fuite == 0 && s.Peur > s.Courage) s.Fuite = 1;
                    else if (s.Fuite != 0 && s.Peur < 0.3f * s.Courage) { s.Fuite = 0; s.Ralliements++; }
                }
                bool fuit = s.Fuite != 0;
                float2 place = Formation.VersMonde(Formation.Place(r, s.Numero) + s.Decalage, r.Position, front);
                float2 pos = t.Position.xz;
                // Les forces d'un homme : la fatigue et les blessures les rongent.
                float vigueur = (1f - 0.5f * s.Fatigue) * (0.4f + 0.6f * math.saturate(s.Sante));
                float forceMax = global::Guerre.Corps.ForceMax(s.Arme, MasseChevaux);
                float fMax = forceMax * vigueur;

                // L'effort vers sa place : fort à l'arrêt, nul quand on y court déjà assez vite.
                float2 vers = place - pos;
                float dist = math.length(vers);
                float2 dir = dist > 0.01f ? vers / dist : float2.zero;
                float gain = math.lerp(3f, 1.4f, math.saturate(dist - 0.5f));
                float vVoulue = math.min(global::Guerre.Corps.VitesseMax(s.Arme) * s.Allure * vigueur, dist * gain);
                if (melee) vVoulue = math.min(vVoulue, VitessePresse);
                float2 fMarche, fLat;
                if (monte)
                {
                    // Un cavalier tient l'allure de sa ligne, et corrige en plus son retard sur sa place :
                    // un cheval met des secondes à prendre le galop, il ne peut pas attendre d'être distancé.
                    float vMax = global::Guerre.Corps.VitesseMax(s.Arme) * s.Allure * vigueur;
                    float2 voulue = r.Vitesse + dir * math.min(vMax, dist * gain);
                    float lv = math.length(voulue);
                    if (lv > vMax) voulue *= vMax / lv;
                    float2 dv = voulue - s.Vitesse;
                    float ldv = math.length(dv);
                    fMarche = ldv > 1e-4f ? dv / ldv * fMax * math.min(1f, ldv / 0.4f) : float2.zero;
                    fLat = float2.zero;
                }
                else if (!melee)
                {
                    float vLong = math.dot(s.Vitesse, dir);
                    fMarche = dir * fMax * math.clamp((vVoulue - vLong) / 0.4f, -1f, 1f);
                    float2 vLat = s.Vitesse - dir * vLong;
                    fLat = -vLat * masse / 0.35f;
                }
                else
                {
                    // Dans la presse, on pousse droit devant et l'on tient sa file : l'effort suit
                    // l'axe du régiment, et l'on revient sur le côté à sa file au lieu de contourner.
                    float2 droite = new float2(front.y, -front.x);
                    float axial = math.dot(vers, front), lateral = math.dot(vers, droite);
                    float vAx = math.dot(s.Vitesse, front), vLa = math.dot(s.Vitesse, droite);
                    float vAxVoulue = math.clamp(axial * gain, -VitessePresse, VitessePresse);
                    // Qui charge pousse de toutes ses forces sur ce qu'il a devant lui : l'ennemi, ou le
                    // dos du camarade qui le précède. Sans rien devant, il ne dépasse pas sa place ;
                    // qui tient ne fait que résister quand on le repousse.
                    // Contre-épreuve : sans poussée, seuls les hommes au contact de l'ennemi appuient
                    // de toutes leurs forces ; les rangs arrière se contentent de tenir leur place.
                    bool pousse = Poussee != 0 || s.Contact != 0;
                    if (pousse && r.Ennemi != Entity.Null && axial > -1.5f && QuelquUnDevant(e, pos, front, rayon)) vAxVoulue = VitessePresse;
                    fMarche = front * fMax * math.clamp((vAxVoulue - vAx) / 0.4f, -1f, 1f);
                    // Coude à coude : on tient sa file fermement, en s'arc-boutant contre ses voisins.
                    float vLaVoulue = math.clamp(lateral * 6f, -1f, 1f);
                    fLat = droite * 2f * fMax * math.clamp((vLaVoulue - vLa) / 0.2f, -1f, 1f);
                }
                float lLat = math.length(fLat), lLatMax = melee ? 2f * fMax : fMax;
                if (lLat > lLatMax) fLat *= lLatMax / lLat;
                if (fuit)
                {
                    // Il fuit : loin de ce qui le menace, ou à défaut à l'opposé de l'ennemi de son régiment.
                    float2 loin = math.lengthsq(menace) > 1e-4f ? math.normalize(menace) : -front;
                    float2 fF = (loin * global::Guerre.Corps.VitesseFuite(s.Arme) - s.Vitesse) * masse / 0.3f;
                    float lF = math.length(fF);
                    fMarche = lF > forceMax ? fF * forceMax / lF : fF;
                    fLat = float2.zero;
                }
                float2 force = fMarche + fLat + forcePiques;

                float presse = 0; byte contact = 0;
                int portee2 = monte ? 2 : 1;   // un cheval touche plus loin qu'une cellule
                int2 c = (int2)math.floor(pos / Cellule);
                if (Corps != 0)
                {
                    for (int dz = -portee2; dz <= portee2; dz++)
                    for (int dx = -portee2; dx <= portee2; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.E == e) continue;
                            // Un homme à terre, on l'enjambe ou on le piétine : il ne pousse personne. Mais un cheval
                            // qui passe sur des corps à terre trébuche, et y laisse de son élan.
                            if (q.AuSol != 0)
                            {
                                float vc = math.length(s.Vitesse);
                                if (monte && vc > 0.3f && math.distancesq(pos, q.P) < math.square(rayon + 0.3f)) force -= s.Vitesse / vc * Trebucher;
                                continue;
                            }
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d);
                            if (l2 < 1e-8f) continue;
                            float l = math.sqrt(l2), diametre = rayon + q.Rayon;
                            bool ennemi = q.Camp != s.Camp, camarade = q.Regiment == s.Regiment.Index;
                            if (!ennemi && !camarade)
                            {
                                // L'espace personnel face aux autres régiments amis : on s'écarte avant de se toucher.
                                float espace = diametre + Marge;
                                if (l < espace) force += d / l * (1f - l / espace) * forceMax * 1.2f;
                            }
                            else if ((ennemi || melee || fuit) && l < diametre)
                            {
                                // Corps contre corps : face à l'ennemi toujours, entre camarades dans la presse.
                                float2 nrm = d / l, tang = new float2(-nrm.y, nrm.x);
                                float2 vRel = s.Vitesse - q.V;
                                float fn = math.max(0f, Raideur * (diametre - l) - Amorti * math.dot(vRel, nrm));
                                // Le frottement : deux corps pressés l'un contre l'autre ne glissent pas l'un sur l'autre.
                                float ft = math.clamp(-Glissement * math.dot(vRel, tang), -Frottement * fn, Frottement * fn);
                                force += nrm * fn + tang * ft;
                                presse += fn;
                                if (ennemi) contact = 1;
                                // Un choc trop brusque pour que le plus léger le suive d'un pas le renverse. Le choc est
                                // alors inélastique : le plus léger part avec le plus lourd, qui y perd d'autant son élan.
                                // Les deux corps font le même calcul, sur les mêmes positions : la quantité de mouvement se conserve.
                                float leger = math.min(masse, q.Masse);
                                if (math.max(masse, q.Masse) > 1.5f * leger && fn > leger * Renversement)
                                {
                                    float rapproche = -math.dot(vRel, nrm);
                                    if (rapproche > 0f) elan += nrm * rapproche * (q.Masse / (masse + q.Masse));
                                    if (masse < q.Masse) renverse = math.max(renverse, fn / (masse * Renversement));
                                }
                            }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                }

                // Renversé : par le choc d'un corps bien plus lourd, ou par sa propre pique qu'un cheval enfonce.
                float seuil = masse * Renversement;
                renverse = math.max(renverse, math.length(choc) / seuil);
                s.Vitesse += elan;
                if (renverse > 1f)
                {
                    s.AuSol = alea0.NextFloat(2.5f, 4.5f);
                    Coups.Enqueue(new Coup { Cible = e, Degats = math.min(0.35f, 0.05f * (renverse - 1f)), Lieu = pos0, Camp = s.Camp });
                    Evenements.Enqueue(4);
                }

                s.Vitesse += force / masse * Dt;
                float v = math.length(s.Vitesse);
                float vPlafond = global::Guerre.Corps.VitesseMax(s.Arme) + 0.9f;
                if (v > vPlafond) { s.Vitesse *= vPlafond / v; }
                float2 avant = pos;
                pos += s.Vitesse * Dt;

                if (Corps != 0)
                {
                    // Hors de la presse, les corps se règlent par placement : le campé tient face
                    // à un régiment ami, et s'efface devant un camarade qui rejoint sa place.
                    // Personne, jamais, n'est écrasé en deçà d'une part du contact ; le plus léger cède.
                    float appui = Appui(s);
                    bool corrige = false;
                    c = (int2)math.floor(pos / Cellule);
                    for (int dz = -portee2; dz <= portee2; dz++)
                    for (int dx = -portee2; dx <= portee2; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.E == e || q.AuSol != 0) continue;
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d), diametre = rayon + q.Rayon;
                            if (l2 >= diametre * diametre) continue;
                            float l = math.sqrt(l2);
                            float2 nrm = l > 1e-4f ? d / l : math.normalizesafe(avant - q.P, new float2(1, 0));
                            bool ennemi = q.Camp != s.Camp, camarade = q.Regiment == s.Regiment.Index;
                            if (!ennemi && !camarade) { pos += nrm * (diametre - l) * (q.Appui / (appui + q.Appui)); corrige = true; }
                            else if (camarade && !melee && !fuit) { pos += nrm * (diametre - l) * (appui / (appui + q.Appui)); corrige = true; }
                            else if (l < Ecrasement * diametre) { pos += nrm * (Ecrasement * diametre - l) * (q.Masse / (masse + q.Masse)); corrige = true; }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                    // Ce qu'on a été empêché de faire, on ne l'a pas fait : l'élan suit le mouvement réel.
                    if (corrige) s.Vitesse = math.lerp(s.Vitesse, (pos - avant) / Dt, 0.5f);
                    v = math.length(s.Vitesse);
                }
                s.Ecart = math.distance(pos, place);
                s.Presse = presse;
                // Une pique dans le poitrail, c'est être au contact de l'ennemi, même sans toucher un corps.
                if (monte && math.lengthsq(forcePiques) > 0f) contact = 1;
                s.Contact = contact;

                // Les coups : l'ennemi le plus proche, devant soi, à portée de son arme (vu plus haut).
                s.APortee = (byte)(trouve ? 1 : 0);
                s.Recharge -= Dt * vigueur;
                // Le tir : un arbalétrier arrêté, que l'ennemi n'a pas encore atteint, vise un homme du
                // régiment ennemi et lâche son carreau quand il a rechargé. La trajectoire est calculée
                // pour atteindre le point visé ; la main tremble d'autant plus qu'on est fatigué.
                bool tire = false;
                if (s.Arme == 2 && r.Tir != 0 && !trouve && s.Fuite == 0 && v < 0.4f && Regiments.HasComponent(r.Ennemi))
                {
                    tire = true;
                    if (s.Recharge <= 0)
                    {
                        var alea = Random.CreateFromIndex((uint)e.Index * 9973u + Graine);
                        var en = Regiments[r.Ennemi];
                        float2 droiteE = new float2(en.Front.y, -en.Front.x);
                        float2 vise2 = en.Position + droiteE * alea.NextFloat(-0.5f, 0.5f) * en.Largeur + en.Front * alea.NextFloat(-0.5f, 0.5f) * en.Profondeur;
                        float3 depart = new float3(pos.x, t.Position.y + 1.45f, pos.y) + new float3(front.x, 0, front.y) * 0.4f;
                        float3 vise = new float3(vise2.x, Sol.Hauteur(ref Relief.Value, vise2) + 1.1f, vise2.y);
                        float3 v0;
                        // On ne tire pas dans le dos d'un camarade : si la trajectoire passe à hauteur de
                        // sa tête, on attend (sans perdre son chargement) qu'elle se dégage.
                        bool degage = true;
                        if (devantX < 1e8f && Balistique(depart, vise, Armes.VitesseCarreau, out v0))
                        {
                            // La distance se compte depuis le départ du carreau, 40 cm devant le tireur.
                            float vh = math.length(v0.xz), tempsV = math.max(devantX - 0.4f, 0f) / math.max(vh, 1f);
                            float hauteur = depart.y + v0.y * tempsV - 0.5f * 9.81f * tempsV * tempsV;
                            degage = hauteur > devantSol + 1.85f;
                        }
                        if (!degage) { }
                        else if (Balistique(depart, vise, Armes.VitesseCarreau, out v0))
                        {
                            // Dispersion : un écart d'angle en hauteur et en direction, qui croît avec la fatigue.
                            float sigma = math.radians(0.9f) * (1f + s.Fatigue);
                            float2 g = Gauss(ref alea) * sigma;
                            v0 = Tourner(v0, g.x, g.y);
                            Tirs.Enqueue(new Tir { P = depart, V = v0, Degats = Armes.DegatsCarreau, Camp = s.Camp });
                        }
                        if (degage)
                        {
                            s.Recharge = Armes.RechargeArbalete * alea.NextFloat(0.8f, 1.2f);
                            s.CoupT = 0;
                            s.Fatigue += 0.005f;
                        }
                    }
                }
                if (trouve && !tire)
                {
                    if (s.Recharge <= 0)
                    {
                        var alea = Random.CreateFromIndex((uint)e.Index * 7919u + Graine);
                        // On ne pare que ce qui vient de devant soi ; qui fuit ou gît à terre ne pare plus rien.
                        bool deFace = math.dot(pos0 - cible.P, cible.Front) > 0;
                        float defense = cible.Fuite != 0 || cible.AuSol != 0 || !deFace ? 0f : 0.6f * (1f - cible.Fatigue) * (1f - math.saturate(cible.Presse / 2500f));
                        // La lance d'un cavalier lancé frappe de tout le poids de son élan.
                        float lancee = monte ? math.max(0f, math.dot(s.Vitesse - cible.V, math.normalizesafe(cible.P - pos0))) / 3f : 0f;
                        if (alea.NextFloat() < 0.2f * (1f - defense))
                            Coups.Enqueue(new Coup { Cible = cible.E, Degats = Armes.Degats(s.Arme) * (1f + lancee * lancee) * (1f - Armes.Armure(cible.Arme)) * alea.NextFloat(0.6f, 1.4f), Lieu = cible.P, Camp = cible.Camp });
                        s.Recharge = Armes.Cadence(s.Arme) * alea.NextFloat(0.8f, 1.2f);
                        s.CoupT = 0;
                        s.Fatigue += 0.01f;
                    }
                }
                else if (!tire) s.Recharge = math.max(s.Recharge, 0.4f);
                s.CoupT += Dt;

                // La fatigue monte avec l'effort et redescend au repos, plus lentement dans la presse.
                float effort = math.saturate(math.length(fMarche) / forceMax);
                s.Fatigue = math.saturate(s.Fatigue + Dt * (0.011f * effort - 0.005f * (1f - effort) * (melee ? 0.3f : 1f)));

                // Le pas suit le chemin réellement parcouru : un homme bousculé ne marche pas sur place.
                // Le cheval allonge sa foulée au galop.
                float galop = monte ? math.smoothstep(4f, 6f, v) : 0f;
                float foulee = monte ? math.lerp(2.6f, 3.8f, galop) : Foulee;
                s.Phase = math.frac(s.Phase + v * Dt / foulee);
                anim.Value = new float4(s.Phase, math.smoothstep(0.12f, 0.6f, v), math.frac(s.Allure * 37.13f), 0);
                // En garde : face à l'ennemi qu'on frappe ou qu'on vise ; piques basses quand l'ennemi approche de front.
                bool enGarde = trouve || tire || (s.Arme == 0 && r.Herisse != 0 && !fuit);
                if (monte) enGarde = trouve && v < 3f;
                float garde = combat.Value.y + math.clamp((enGarde ? 1f : 0f) - combat.Value.y, -Dt * 3f, Dt * 3f);
                s.Garde = garde;
                // Derrière son pavois, on s'abrite à genou ; on ne se lève que pour viser, la dernière
                // seconde et demie avant de lâcher son carreau. Le cavalier, lui, couche sa lance au galop.
                bool enJoue = tire && s.Recharge < 1.5f;
                float abri = s.Poste != 0 && !enJoue && !trouve ? 1f : 0f;
                s.Abri += math.clamp(abri - s.Abri, -Dt * 2.5f, Dt * 2.5f);
                combat.Value = new float4(math.min(s.CoupT, 0.999f), garde, monte ? galop : s.Abri, 0);
                float y = Sol.Hauteur(ref Relief.Value, pos);

                // On regarde l'ennemi qu'on frappe ; sinon où l'on va, sauf à reculer : on garde alors le front.
                // Un cheval ne recule pas en regardant ailleurs que devant lui : il regarde où il va.
                float2 dirV = v > 0.35f ? s.Vitesse / v : front;
                // Le piquier en hérisson tient sa pique droit devant : une hampe de cinq mètres ne se braque pas.
                bool herisson = s.Arme == 0 && r.Herisse != 0 && !fuit;
                bool faceACible = trouve && !(monte && v > 2f) && !herisson;
                float2 regard = herisson ? front : faceACible ? math.normalizesafe(cible.P - pos, front) : fuit || math.dot(dirV, front) > -0.2f ? dirV : front;
                var rot = quaternion.LookRotationSafe(new float3(regard.x, 0, regard.y), math.up());
                t.Rotation = math.slerp(t.Rotation, rot, math.saturate(Dt * (monte ? 3f : 5f)));
                t.Position = new float3(pos.x, y, pos.y);
                // Le pavois : un arbalétrier arrêté, hors de la presse et qui ne fuit pas, le plante devant lui.
                s.Regard = math.normalizesafe(math.forward(t.Rotation).xz, front);
                s.Poste = (byte)(s.Arme == 2 && Pavois != 0 && r.SansPavois == 0 && v < 0.4f && !melee && s.Fuite == 0 ? 1 : 0);
                s.Lieu = t.Position;
            }

            // Vitesse de départ pour atteindre un point avec une vitesse donnée, sur l'arc tendu.
            static bool Balistique(float3 a, float3 b, float vitesse, out float3 v0)
            {
                const float g = 9.81f;
                float2 h = b.xz - a.xz;
                float dx = math.length(h), dy = b.y - a.y, v2 = vitesse * vitesse;
                float disc = v2 * v2 - g * (g * dx * dx + 2f * dy * v2);
                v0 = default;
                if (disc < 0 || dx < 1f) return false;
                float angle = math.atan((v2 - math.sqrt(disc)) / (g * dx));
                float2 dir = h / dx;
                v0 = new float3(dir.x * math.cos(angle), math.sin(angle), dir.y * math.cos(angle)) * vitesse;
                return true;
            }

            static float2 Gauss(ref Random alea)
            {
                float u1 = math.max(alea.NextFloat(), 1e-6f), u2 = alea.NextFloat();
                float rayon = math.sqrt(-2f * math.log(u1));
                return new float2(rayon * math.cos(2 * math.PI * u2), rayon * math.sin(2 * math.PI * u2));
            }

            // Tourne une vitesse d'un angle en hauteur puis en direction.
            static float3 Tourner(float3 v, float hauteur, float direction)
            {
                float3 axe = math.normalizesafe(math.cross(v, math.up()), new float3(1, 0, 0));
                v = math.mul(quaternion.AxisAngle(axe, -hauteur), v);
                return math.mul(quaternion.RotateY(direction), v);
            }
        }

        // Les carreaux en vol : la gravité les courbe ; ils s'arrêtent sur le premier corps, le premier
        // pavois ou le sol qu'ils rencontrent. Un carreau peut toucher un ami qui se trouve sur sa route.
        [BurstCompile]
        partial struct Voler : IJobEntity
        {
            [ReadOnly] public NativeParallelMultiHashMap<int, Voisin> Grille;
            [ReadOnly] public NativeParallelMultiHashMap<int, PavoisPlante> Plantes;
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            public NativeQueue<Coup>.ParallelWriter Coups;
            public NativeQueue<byte>.ParallelWriter Evenements;
            public float Dt;
            public uint Graine;

            const float Rayon = 0.22f, RayonCheval = 0.5f;   // un homme, un cheval vu de face ou de flanc

            void Execute(Entity e, ref Projectile p, ref LocalTransform t)
            {
                if (p.Etat == 0) return;
                if (p.Etat >= 2)
                {
                    p.Vie -= Dt;
                    if (p.Vie <= 0) { p.Etat = 0; t = LocalTransform.FromPositionRotationScale(new float3(0, -100, 0), quaternion.identity, 0); }
                    return;
                }
                float3 a = p.P;
                p.V.y -= 9.81f * Dt;
                float3 b = a + p.V * Dt;
                float3 d = b - a;
                float meilleur = 1f; int quoi = 0; Voisin cible = default;
                int2 c = (int2)math.floor(b.xz / Cellule);
                for (int dz = -1; dz <= 1; dz++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                    do
                    {
                        float sol = Sol.Hauteur(ref Relief.Value, q.P);
                        // Le corps : un cylindre debout, dont on cherche le point le plus proche du trajet.
                        float2 d2 = d.xz;
                        float l2 = math.lengthsq(d2);
                        float u2 = l2 > 1e-8f ? math.saturate(math.dot(q.P - a.xz, d2) / l2) : 0f;
                        float2 proche = a.xz + d2 * u2;
                        float hauteur = a.y + d.y * u2;
                        if (u2 < meilleur && math.lengthsq(proche - q.P) < math.square(Corps.Monte(q.Arme) ? RayonCheval : Rayon) && hauteur > sol && hauteur < sol + q.Taille)
                        { meilleur = u2; quoi = 2; cible = q; }
                    } while (Grille.TryGetNextValue(out q, ref it));
                }

                // Les pavois plantés : des panneaux verticaux posés dans le monde, qu'on traverse ou non.
                for (int dz = -1; dz <= 1; dz++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    if (!Plantes.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var pv, out var it)) continue;
                    do
                    {
                        float2 centre = pv.Base.xz;
                        float da = math.dot(a.xz - centre, pv.Normale), db = math.dot(b.xz - centre, pv.Normale);
                        if (da * db >= 0) continue;
                        float u = da / (da - db);
                        float3 i = a + d * u;
                        float cote = math.dot(i.xz - centre, new float2(-pv.Normale.y, pv.Normale.x));
                        if (u < meilleur && math.abs(cote) < Armes.PavoisLargeur * 0.5f && i.y > pv.Base.y && i.y < pv.Base.y + Armes.PavoisHauteur)
                        { meilleur = u; quoi = 1; }
                    } while (Plantes.TryGetNextValue(out pv, ref it));
                }

                if (quoi == 1)
                {
                    p.Etat = 3; p.Vie = 8f; p.P = a + d * meilleur;
                    Evenements.Enqueue(1);
                }
                else if (quoi == 2)
                {
                    var alea = Random.CreateFromIndex((uint)e.Index * 7919u + Graine);
                    Coups.Enqueue(new Coup { Cible = cible.E, Degats = p.Degats * (1f - Armes.Armure(cible.Arme)) * alea.NextFloat(0.6f, 1.4f), Lieu = cible.P, Camp = cible.Camp });
                    p.Etat = 0;
                    t = LocalTransform.FromPositionRotationScale(new float3(0, -100, 0), quaternion.identity, 0);
                    return;
                }
                else
                {
                    float sol = Sol.Hauteur(ref Relief.Value, b.xz);
                    if (b.y <= sol) { p.Etat = 2; p.Vie = 8f; p.P = new float3(b.x, sol + 0.05f, b.z); Evenements.Enqueue(2); }
                    else p.P = b;
                }
                t = LocalTransform.FromPositionRotation(p.P, quaternion.LookRotationSafe(p.V, math.up()));
            }
        }

        // Les tirs de l'image prennent chacun un carreau libre du réservoir.
        [BurstCompile]
        partial struct Lancer : IJobEntity
        {
            public NativeQueue<Tir> Tirs;
            public NativeQueue<byte>.ParallelWriter Evenements;
            void Execute(ref Projectile p, ref LocalTransform t)
            {
                if (p.Etat != 0 || !Tirs.TryDequeue(out var tir)) return;
                p = new Projectile { P = tir.P, V = tir.V, Degats = tir.Degats, Camp = tir.Camp, Etat = 1 };
                t = LocalTransform.FromPositionRotation(tir.P, quaternion.LookRotationSafe(tir.V, math.up()));
                Evenements.Enqueue(3);
            }
        }

        [BurstCompile]
        struct ViderTirs : IJob
        {
            public NativeQueue<Tir> Tirs;
            public void Execute() => Tirs.Clear();
        }

        [BurstCompile]
        struct ViderEvenements : IJob
        {
            public NativeQueue<byte> Evenements;
            public void Execute() => Evenements.Clear();
        }

        [BurstCompile]
        struct Compter : IJob
        {
            public NativeQueue<byte> Evenements;
            public ComponentLookup<CompteTir> Compte;
            public Entity Entite;
            public void Execute()
            {
                var c = Compte[Entite];
                while (Evenements.TryDequeue(out var ev))
                {
                    if (ev == 1) c.Pavois++;
                    else if (ev == 2) c.AuSol++;
                    else if (ev == 3) c.Tires++;
                    else if (ev == 4) c.Renverses++;
                    else if (ev == 5) c.PiquesRompues++;
                }
                Compte[Entite] = c;
            }
        }

        [BurstCompile]
        struct Appliquer : IJob
        {
            public NativeQueue<Coup> Coups;
            public ComponentLookup<Soldat> Soldats;
            public ComponentLookup<Regiment> Regiments;
            public NativeParallelHashMap<int, float2> Effroi;
            public byte Peur;
            public void Execute()
            {
                Effroi.Clear();
                while (Coups.TryDequeue(out var c))
                {
                    if (!Soldats.HasComponent(c.Cible)) continue;
                    var s = Soldats[c.Cible];
                    bool vivant = s.Sante > 0;
                    s.Sante -= c.Degats;
                    s.Touches++;
                    if (Regiments.HasComponent(s.Regiment)) { var rg = Regiments[s.Regiment]; rg.Touches++; Regiments[s.Regiment] = rg; }
                    // Être blessé fait peur.
                    if (Peur != 0) s.Peur = math.saturate(s.Peur + c.Degats * 0.6f);
                    Soldats[c.Cible] = s;
                    if (vivant && s.Sante <= 0)
                    {
                        int k = CleEffroi(c.Lieu);
                        Effroi.TryGetValue(k, out var m);
                        Effroi[k] = m + (c.Camp == 0 ? new float2(1, 0) : new float2(0, 1));
                    }
                }
            }
        }
    }

    // L'écart moyen des hommes à leur place remonte au régiment, avec le nombre de ceux
    // qui touchent l'ennemi : c'est ainsi qu'un ordre attend ceux qu'il commande, et
    // qu'un régiment sait qu'il est dans la mêlée.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemePilotage))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemeCohesion : ISystem
    {
        NativeArray<float4> sommes, centres;
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
            if (centres.IsCreated) centres.Dispose();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            int n = regimentsQuery.CalculateEntityCount();
            if (!sommes.IsCreated || sommes.Length < n)
            {
                state.Dependency.Complete();
                if (sommes.IsCreated) sommes.Dispose();
                if (centres.IsCreated) centres.Dispose();
                sommes = new NativeArray<float4>(math.max(n, 64), Allocator.Persistent);
                centres = new NativeArray<float4>(math.max(n, 64), Allocator.Persistent);
            }
            regiments.Update(ref state);
            var dep = new Additionner { Sommes = sommes, Centres = centres, Regiments = regiments }.Schedule(state.Dependency);
            state.Dependency = new Reporter { Sommes = sommes, Centres = centres }.Schedule(dep);
        }

        [BurstCompile]
        partial struct Additionner : IJobEntity
        {
            public NativeArray<float4> Sommes, Centres;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            void Execute(in Soldat s, in LocalTransform t)
            {
                int i = Regiments[s.Regiment].Index;
                if (s.Fuite != 0) { Sommes[i] += new float4(0, 0, 0, 1); return; }
                Sommes[i] += new float4(s.Ecart, 1, s.Contact, 0);
                Centres[i] += new float4(t.Position.x, t.Position.z, 0, 0);
            }
        }

        [BurstCompile]
        partial struct Reporter : IJobEntity
        {
            public NativeArray<float4> Sommes, Centres;
            void Execute(ref Regiment r)
            {
                var s = Sommes[r.Index];
                r.Ecart = s.y > 0 ? s.x / s.y : 0;
                r.Contacts = (int)s.z;
                r.CentreHommes = s.y > 0 ? Centres[r.Index].xy / s.y : r.Position;
                r.Fuyards = s.y + s.w > 0 ? s.w / (s.y + s.w) : 0;
                Sommes[r.Index] = float4.zero;
                Centres[r.Index] = float4.zero;
            }
        }
    }

    // Les hommes tombés restent sur le terrain, couchés, sans plus de place dans les rangs.
    // Deux fois par seconde, les régiments qui ont perdu du monde referment leurs rangs : un vide
    // laissé ouvert, l'ennemi qui pousse s'y engouffre.
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemeCohesion))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial class SystemePertes : SystemBase
    {
        public static readonly int[] Pertes = new int[2];
        readonly HashSet<Entity> aReclasser = new HashSet<Entity>();
        double prochain;

        protected override void OnCreate() { Pertes[0] = Pertes[1] = 0; }

        protected override void OnUpdate()
        {
            var morts = new NativeList<Entity>(Allocator.Temp);
            foreach (var (s, e) in SystemAPI.Query<RefRO<Soldat>>().WithEntityAccess())
                if (s.ValueRO.Sante <= 0) morts.Add(e);
            var em = EntityManager;
            foreach (var e in morts)
            {
                var s = em.GetComponentData<Soldat>(e);
                var t = em.GetComponentData<LocalTransform>(e);
                // Il tombe à la renverse, les pieds où il se tenait (s'il n'est pas déjà à terre) ;
                // un cheval s'abat sur le flanc, son cavalier avec lui.
                if (Corps.Monte(s.Arme)) { t.Rotation = math.mul(t.Rotation, quaternion.RotateZ(math.PI / 2)); t.Position.y += 0.35f; }
                else if (s.AuSol <= 0) { t.Rotation = math.mul(t.Rotation, quaternion.RotateX(-math.PI / 2)); t.Position.y += 0.12f; }
                em.SetComponentData(e, t);
                em.SetComponentData(e, new AnimEtat { Value = new float4(0, 0, 0, -1) });
                em.SetComponentData(e, new AnimCombat());
                Pertes[s.Camp]++;
                if (em.Exists(s.Regiment))
                {
                    var r = em.GetComponentData<Regiment>(s.Regiment);
                    r.Effectif = math.max(0, r.Effectif - 1);
                    em.SetComponentData(s.Regiment, r);
                    aReclasser.Add(s.Regiment);
                }
                em.RemoveComponent<Soldat>(e);
                em.AddComponentData(e, new Mort { Camp = s.Camp });
            }
            if (aReclasser.Count > 0 && SystemAPI.Time.ElapsedTime >= prochain)
            {
                prochain = SystemAPI.Time.ElapsedTime + 0.5;
                Rangs.Reclasser(em, new List<Entity>(aReclasser));
                aReclasser.Clear();
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
