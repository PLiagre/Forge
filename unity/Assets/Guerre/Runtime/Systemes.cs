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
            for (int i = 0; i < regs.Length; i++)
            {
                var r = regs[i];
                r.Melee = r.Contacts > 0 ? 2f : math.max(0, r.Melee - dt);
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
                if (r.Contacts > 0 && r.Ennemi != Entity.Null)
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

    // Chaque soldat est un corps de 80 kg. Il pousse vers sa place avec une force
    // qui faiblit à mesure qu'il prend de la vitesse, comme un muscle ; les corps en
    // contact se repoussent comme des ressorts. Une file qui pousse transmet donc
    // l'effort de chacun de ses hommes jusqu'au premier rang : dix rangs poussent plus
    // fort que cinq, sans qu'aucune règle ne le dise.
    // À portée d'un ennemi, il frappe à son rythme ; le coup porte d'autant plus
    // souvent que la cible est fatiguée ou écrasée par la presse, qui l'empêche de parer.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemeRegiments))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemePilotage : ISystem
    {
        public const float Cellule = 1.2f;
        NativeParallelMultiHashMap<int, Voisin> grille;
        NativeQueue<Coup> coups;
        NativeParallelHashMap<int, float2> effroi;   // morts de l'image précédente, par case de 4 m et par camp
        ComponentLookup<Regiment> regiments;
        ComponentLookup<Soldat> soldatsRW;
        EntityQuery soldats;
        uint image;

        public void OnCreate(ref SystemState state)
        {
            grille = new NativeParallelMultiHashMap<int, Voisin>(16384, Allocator.Persistent);
            coups = new NativeQueue<Coup>(Allocator.Persistent);
            effroi = new NativeParallelHashMap<int, float2>(1024, Allocator.Persistent);
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
            soldatsRW.Update(ref state);
            var relief = SystemAPI.GetSingleton<Relief>().Blob;
            // Le pas est fixe (Bataille.PasSimulation) ; la borne ne sert qu'en cas d'appel hors du pas fixe.
            float dt = math.min(SystemAPI.Time.DeltaTime, 1f / 30f);
            if (dt <= 0) return;
            var reglages = SystemAPI.TryGetSingleton<ReglagesSimulation>(out var rg) ? rg : new ReglagesSimulation { Corps = 1, Poussee = 1, Peur = 1 };
            image++;

            var dep = new ViderGrille { Grille = grille }.Schedule(state.Dependency);
            dep = new RemplirGrille { Grille = grille.AsParallelWriter(), Regiments = regiments }.ScheduleParallel(dep);
            dep = new Piloter
            {
                Grille = grille, Regiments = regiments, Relief = relief, Dt = dt, Corps = reglages.Corps,
                Poussee = reglages.Poussee, Peur = reglages.Peur, Effroi = effroi, Coups = coups.AsParallelWriter(), Graine = image * 2654435761u,
            }.ScheduleParallel(dep);
            // Les morts de cette image seront vus par leurs voisins à l'image suivante.
            dep = new Appliquer { Coups = coups, Soldats = soldatsRW, Effroi = effroi, Peur = reglages.Peur }.Schedule(dep);
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
        }

        public const float CaseEffroi = 4f;
        public static int CleEffroi(float2 p) => Cle((int2)math.floor(p / CaseEffroi));

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
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            void Execute(Entity e, in Soldat s, in LocalTransform t)
            {
                float2 p = t.Position.xz;
                Grille.Add(Cle((int2)math.floor(p / Cellule)), new Voisin
                {
                    P = p, V = s.Vitesse, E = e, Regiment = s.Regiment.Index, Camp = s.Camp, Arme = s.Arme, Fuite = s.Fuite,
                    Appui = Appui(s), Fatigue = s.Fatigue, Presse = s.Presse, Peur = s.Peur, Front = Regiments[s.Regiment].Front,
                });
            }
        }

        [BurstCompile]
        partial struct Piloter : IJobEntity
        {
            [ReadOnly] public NativeParallelMultiHashMap<int, Voisin> Grille;
            [ReadOnly] public ComponentLookup<Regiment> Regiments;
            [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
            [ReadOnly] public NativeParallelHashMap<int, float2> Effroi;
            public NativeQueue<Coup>.ParallelWriter Coups;
            public float Dt;
            public byte Corps, Poussee, Peur;
            public uint Graine;

            const float Masse = 80f;          // kg, homme et équipement
            const float ForceMax = 400f;      // N : ce qu'un homme frais pousse, arc-bouté
            const float Raideur = 80000f;     // N/m : un corps, une armure, un bouclier écrasés
            const float Amorti = 2400f;       // N·s/m : les corps ne rebondissent pas
            const float Frottement = 0.8f;    // coefficient entre deux corps : armures, boucliers, mains qui agrippent
            const float Glissement = 3000f;   // N·s/m : régularise le frottement à faible vitesse
            const float Rayon = 0.85f;        // distance à laquelle deux hommes de régiments amis se gênent
            const float Diametre = 0.8f;      // épaules, bouclier, coudes
            const float DiametreMin = 0.45f;  // en deçà, même la presse ne peut plus écraser deux hommes
            const float VitesseMax = 2.6f;    // m/s : le pas de course pour rattraper sa place
            const float VitessePresse = 0.5f; // m/s : dans la presse, on avance pas à pas
            const float Foulee = 1.5f;        // m parcourus par cycle de marche cuit (deux pas)
            const float VitesseFuite = 3.2f;  // m/s : on court, l'arme jetée ou non
            const float Vue = 3.6f;           // m : ce qu'un homme perçoit autour de lui dans la mêlée

            // Un corps touche devant soi (à un cône de 50° près) : c'est sur lui qu'on appuie.
            bool QuelquUnDevant(Entity e, float2 pos, float2 front)
            {
                int2 c = (int2)math.floor(pos / Cellule);
                for (int dz = -1; dz <= 1; dz++)
                for (int dx = -1; dx <= 1; dx++)
                {
                    if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                    do
                    {
                        if (q.E == e) continue;
                        float2 d = q.P - pos;
                        float l = math.length(d);
                        if (l < Diametre + 0.1f && math.dot(d, front) > 0.64f * l) return true;
                    } while (Grille.TryGetNextValue(out q, ref it));
                }
                return false;
            }

            void Execute(Entity e, ref Soldat s, ref LocalTransform t, ref AnimEtat anim, ref AnimCombat combat)
            {
                var r = Regiments[s.Regiment];
                bool melee = r.Melee > 0;
                float2 front = r.Front;
                float2 pos0 = t.Position.xz;

                // Ce qu'il voit autour de lui : l'ennemi à portée devant lui, la menace, ses camarades
                // et leur peur. Rien de cela n'est un modificateur : ce sont des perceptions.
                bool trouve = false; Voisin cible = default;
                float2 menace = float2.zero; int ennemisProches = 0, camaradesProches = 0, ennemisHorsDeVue = 0;
                float peurVoisins = 0; int nPeur = 0;
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
                                if (l2 < 1.5f * 1.5f && q.Fuite == 0) camaradesProches++;
                                if (l2 < 2.4f * 2.4f) { peurVoisins += q.Peur; nPeur++; }
                                continue;
                            }
                            if (l2 < Vue * Vue && q.Fuite == 0)
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
                float fMax = ForceMax * vigueur;

                // L'effort vers sa place : fort à l'arrêt, nul quand on y court déjà assez vite.
                float2 vers = place - pos;
                float dist = math.length(vers);
                float2 dir = dist > 0.01f ? vers / dist : float2.zero;
                float gain = math.lerp(3f, 1.4f, math.saturate(dist - 0.5f));
                float vVoulue = math.min(VitesseMax * s.Allure * vigueur, dist * gain);
                if (melee) vVoulue = math.min(vVoulue, VitessePresse);
                float2 fMarche, fLat;
                if (!melee)
                {
                    float vLong = math.dot(s.Vitesse, dir);
                    fMarche = dir * fMax * math.clamp((vVoulue - vLong) / 0.4f, -1f, 1f);
                    float2 vLat = s.Vitesse - dir * vLong;
                    fLat = -vLat * Masse / 0.35f;
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
                    if (pousse && r.Ennemi != Entity.Null && axial > -1.5f && QuelquUnDevant(e, pos, front)) vAxVoulue = VitessePresse;
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
                    float2 fF = (loin * VitesseFuite - s.Vitesse) * Masse / 0.3f;
                    float lF = math.length(fF);
                    fMarche = lF > ForceMax ? fF * ForceMax / lF : fF;
                    fLat = float2.zero;
                }
                float2 force = fMarche + fLat;

                float presse = 0; byte contact = 0;
                int2 c = (int2)math.floor(pos / Cellule);
                if (Corps != 0)
                {
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.E == e) continue;
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d);
                            if (l2 < 1e-8f) continue;
                            float l = math.sqrt(l2);
                            bool ennemi = q.Camp != s.Camp, camarade = q.Regiment == s.Regiment.Index;
                            if (!ennemi && !camarade)
                            {
                                // L'espace personnel face aux autres régiments amis : on s'écarte avant de se toucher.
                                if (l < Rayon) force += d / l * (1f - l / Rayon) * ForceMax * 1.2f;
                            }
                            else if ((ennemi || melee || fuit) && l < Diametre)
                            {
                                // Corps contre corps : face à l'ennemi toujours, entre camarades dans la presse.
                                float2 nrm = d / l, tang = new float2(-nrm.y, nrm.x);
                                float2 vRel = s.Vitesse - q.V;
                                float fn = math.max(0f, Raideur * (Diametre - l) - Amorti * math.dot(vRel, nrm));
                                // Le frottement : deux corps pressés l'un contre l'autre ne glissent pas l'un sur l'autre.
                                float ft = math.clamp(-Glissement * math.dot(vRel, tang), -Frottement * fn, Frottement * fn);
                                force += nrm * fn + tang * ft;
                                presse += fn;
                                if (ennemi) contact = 1;
                            }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                }

                s.Vitesse += force / Masse * Dt;
                float v = math.length(s.Vitesse);
                if (v > 3.5f) { s.Vitesse *= 3.5f / v; }
                float2 avant = pos;
                pos += s.Vitesse * Dt;

                if (Corps != 0)
                {
                    // Hors de la presse, les corps se règlent par placement : le campé tient face
                    // à un régiment ami, et s'efface devant un camarade qui rejoint sa place.
                    // Personne, jamais, n'est écrasé à moins de DiametreMin d'un autre.
                    float appui = Appui(s);
                    bool corrige = false;
                    c = (int2)math.floor(pos / Cellule);
                    for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        if (!Grille.TryGetFirstValue(Cle(c + new int2(dx, dz)), out var q, out var it)) continue;
                        do
                        {
                            if (q.E == e) continue;
                            float2 d = pos - q.P;
                            float l2 = math.lengthsq(d);
                            if (l2 >= Diametre * Diametre) continue;
                            float l = math.sqrt(l2);
                            float2 nrm = l > 1e-4f ? d / l : math.normalizesafe(avant - q.P, new float2(1, 0));
                            bool ennemi = q.Camp != s.Camp, camarade = q.Regiment == s.Regiment.Index;
                            if (!ennemi && !camarade) { pos += nrm * (Diametre - l) * (q.Appui / (appui + q.Appui)); corrige = true; }
                            else if (camarade && !melee && !fuit) { pos += nrm * (Diametre - l) * (appui / (appui + q.Appui)); corrige = true; }
                            else if (l < DiametreMin) { pos += nrm * (DiametreMin - l) * 0.5f; corrige = true; }
                        } while (Grille.TryGetNextValue(out q, ref it));
                    }
                    // Ce qu'on a été empêché de faire, on ne l'a pas fait : l'élan suit le mouvement réel.
                    if (corrige) s.Vitesse = math.lerp(s.Vitesse, (pos - avant) / Dt, 0.5f);
                    v = math.length(s.Vitesse);
                }
                s.Ecart = math.distance(pos, place);
                s.Presse = presse;
                s.Contact = contact;

                // Les coups : l'ennemi le plus proche, devant soi, à portée de son arme (vu plus haut).
                s.APortee = (byte)(trouve ? 1 : 0);
                s.Recharge -= Dt * vigueur;
                if (trouve)
                {
                    if (s.Recharge <= 0)
                    {
                        var alea = Random.CreateFromIndex((uint)e.Index * 7919u + Graine);
                        // On ne pare que ce qui vient de devant soi ; qui fuit ne pare plus rien.
                        bool deFace = math.dot(pos0 - cible.P, cible.Front) > 0;
                        float defense = cible.Fuite != 0 || !deFace ? 0f : 0.6f * (1f - cible.Fatigue) * (1f - math.saturate(cible.Presse / 2500f));
                        if (alea.NextFloat() < 0.2f * (1f - defense))
                            Coups.Enqueue(new Coup { Cible = cible.E, Degats = Armes.Degats(s.Arme) * (1f - Armes.Armure(cible.Arme)) * alea.NextFloat(0.6f, 1.4f), Lieu = cible.P, Camp = cible.Camp });
                        s.Recharge = Armes.Cadence(s.Arme) * alea.NextFloat(0.8f, 1.2f);
                        s.CoupT = 0;
                        s.Fatigue += 0.01f;
                    }
                }
                else s.Recharge = math.max(s.Recharge, 0.4f);
                s.CoupT += Dt;

                // La fatigue monte avec l'effort et redescend au repos, plus lentement dans la presse.
                float effort = math.saturate(math.length(fMarche) / ForceMax);
                s.Fatigue = math.saturate(s.Fatigue + Dt * (0.011f * effort - 0.005f * (1f - effort) * (melee ? 0.3f : 1f)));

                // Le pas suit le chemin réellement parcouru : un homme bousculé ne marche pas sur place.
                s.Phase = math.frac(s.Phase + v * Dt / Foulee);
                anim.Value = new float4(s.Phase, math.smoothstep(0.12f, 0.6f, v), math.frac(s.Allure * 37.13f), 0);
                float garde = combat.Value.y + math.clamp((trouve ? 1f : 0f) - combat.Value.y, -Dt * 3f, Dt * 3f);
                combat.Value = new float4(math.min(s.CoupT, 0.999f), garde, 0, 0);
                float y = Sol.Hauteur(ref Relief.Value, pos);

                // On regarde l'ennemi qu'on frappe ; sinon où l'on va, sauf à reculer : on garde alors le front.
                float2 dirV = v > 0.35f ? s.Vitesse / v : front;
                float2 regard = trouve ? math.normalizesafe(cible.P - pos, front) : fuit || math.dot(dirV, front) > -0.2f ? dirV : front;
                var rot = quaternion.LookRotationSafe(new float3(regard.x, 0, regard.y), math.up());
                t.Rotation = math.slerp(t.Rotation, rot, math.saturate(Dt * 5f));
                t.Position = new float3(pos.x, y, pos.y);
            }
        }

        [BurstCompile]
        struct Appliquer : IJob
        {
            public NativeQueue<Coup> Coups;
            public ComponentLookup<Soldat> Soldats;
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
                // Il tombe à la renverse, les pieds où il se tenait.
                t.Rotation = math.mul(t.Rotation, quaternion.RotateX(-math.PI / 2));
                t.Position.y += 0.12f;
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
