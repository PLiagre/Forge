using Unity.Entities;
using Unity.Mathematics;
using Unity.Rendering;

namespace Guerre
{
    // Un soldat est une personne : son numéro dans le régiment, son élan, son pas.
    // Le régiment ne marche pas à sa place, il lui dit seulement où se tenir.
    public struct Soldat : IComponentData
    {
        public Entity Regiment;
        public int Numero;       // rang d'appel dans le régiment : sa place se déduit de la formation
        public float2 Decalage;  // quelques centimètres : personne ne se tient au cordeau
        public float2 Vitesse;   // m/s, dans le plan
        public float Phase;      // cycles de marche accomplis : un cycle vaut deux pas
        public float Allure;     // 0,9 à 1,1 : tous les hommes ne marchent pas au même train
        public float Ecart;      // distance à sa place, en mètres, à la dernière image
        public float3 Teinte;
        public byte Camp, Arme;
        // Le combat.
        public float Sante;      // 1 : indemne ; 0 : mort
        public float Fatigue;    // 0 : frais ; 1 : épuisé
        public float Recharge;   // secondes avant de pouvoir porter un nouveau coup
        public float CoupT;      // secondes depuis le dernier coup porté (pour l'animation)
        public float Presse;     // force de contact reçue des corps voisins, en newtons
        public byte Contact;     // 1 : touche un ennemi, corps contre corps
        public byte APortee;     // 1 : un ennemi est à portée de son arme
        // La peur : ce qu'il a vu et subi, et ce que ressentent ses voisins.
        public float Peur;       // 0 : calme ; au-delà de son courage, il fuit
        public float Courage;    // seuil propre à chacun
        public byte Fuite;       // 1 : il fuit
        public int Ralliements;  // nombre de fois qu'il est revenu après avoir fui
        // Le tir et le pavois.
        public byte Poste;       // 1 : arbalétrier arrêté, son pavois planté devant lui
        public float2 Regard;    // vers où il fait face (et son pavois avec lui)
        public float3 Lieu;      // sa position, lue par son pavois
        public int Touches;      // coups et carreaux reçus
        public float Abri;           // 0 debout ; 1 à genou derrière son pavois
        // La cavalerie et les piques.
        public float AuSol;          // secondes avant de se relever, renversé par un cheval ; 0 : debout
        public float Garde;          // 0..1 : l'arme en garde ; une pique n'arrête un cheval que baissée
        public byte Brisee;          // 1 : sa pique s'est rompue dans le poitrail d'un cheval
    }

    // Un carreau d'arbalète : un réservoir fixe de carreaux est levé une fois, puis réutilisé.
    public struct Projectile : IComponentData
    {
        public float3 P, V;      // position et vitesse, en mètres et m/s
        public float Vie;        // secondes restantes, planté au sol ou dans un pavois
        public float Degats;
        public byte Camp;        // camp du tireur
        public byte Etat;        // 0 libre, 1 en vol, 2 planté au sol, 3 planté dans un pavois
    }

    // Un tir décidé par un arbalétrier, en attente d'un carreau libre.
    public struct Tir
    {
        public float3 P, V;
        public float Degats;
        public byte Camp;
    }

    // Le pavois d'un arbalétrier : planté devant lui à l'arrêt, porté dans son dos en marche.
    public struct Pavois : IComponentData
    {
        public Entity Porteur;
        public byte Plante, Tombe;   // planté dans le sol ; tombé à plat avec son porteur mort
        public float3 Base;          // où il est planté
        public float2 Normale;       // vers où il fait face
    }

    // Les comptes du tir, pour les essais et l'affichage.
    public struct CompteTir : IComponentData
    {
        public int Tires, Pavois, AuSol;
        public int Renverses, PiquesRompues;   // hommes renversés par un cheval ; piques rompues dans un poitrail
    }

    // Un homme tombé : il ne marche plus, ne pousse plus, reste sur le terrain.
    public struct Mort : IComponentData
    {
        public byte Camp;
    }

    // L'état de combat lu par le shader : x phase du coup (0..1), y poids de la garde.
    [MaterialProperty("_AnimCombat")]
    public struct AnimCombat : IComponentData
    {
        public float4 Value;
    }

    // Un coup qui porte, en attente d'être appliqué à sa cible.
    public struct Coup
    {
        public Entity Cible;
        public float Degats;
        public float2 Lieu;      // où se tient la cible : si le coup la tue, ses voisins le voient
        public byte Camp;        // camp de la cible
    }

    // Les armes, par indice d'arme. Des ordres de grandeur, à régler en jouant :
    // aucune n'est une règle de victoire, seulement une portée, un rythme, un poids.
    public static class Armes
    {
        // L'arbalète de guerre, armée au cranequin : un carreau lancé à 55 m/s, deux à trois par minute.
        // On tire sur une troupe en masse jusqu'à 230 m : la trajectoire en cloche passe par-dessus ses rangs.
        public const float VitesseCarreau = 55f, DegatsCarreau = 0.6f, RechargeArbalete = 20f, PorteeTir = 230f;
        // Le pavois : un panneau de bois planté à 55 cm devant soi.
        public const float PavoisLargeur = 0.9f, PavoisHauteur = 1.25f, PavoisDistance = 0.55f;
        // Pique, hallebarde, dague, et la lance du cavalier, comptée depuis le centre du cheval.
        public static float Portee(int a) => a == 0 ? 3.2f : a == 1 ? 1.9f : a == 2 ? 1.1f : 3.3f;
        public static float Cadence(int a) => a == 0 ? 3.2f : a == 1 ? 3.8f : a == 2 ? 2.4f : 3.0f;  // secondes entre deux coups
        public static float Degats(int a) => a == 0 ? 0.22f : a == 1 ? 0.4f : a == 2 ? 0.18f : 0.25f;
        // Part du coup arrêtée : l'homme d'armes porte le harnois, son cheval une housse sur du cuir.
        public static float Armure(int a) => a == 0 ? 0.15f : a == 1 ? 0.45f : a == 2 ? 0.05f : 0.5f;
        // La pique contre le cheval : plantée en terre, elle plie jusqu'à ForcePique ; son fer entre dans le
        // poitrail, et la hampe se rompt quand il y est enfoncé de PiqueRompue.
        // Un cheval meurt d'avoir absorbé EnergieMortelle joules sur des fers : un fer enfoncé d'un demi-mètre
        // dans le poitrail. La housse ne l'arrête pas, le harnois du cavalier non plus.
        public const float RaideurPique = 60000f, ForcePique = 5000f, PiqueRompue = 1.2f, EnergieMortelle = 2500f;
    }

    // Les corps : un homme à pied, ou un cheval et son cavalier. Rien ici ne dit qui gagne :
    // seulement une masse, une taille, une force et une allure.
    public static class Corps
    {
        public const int Cavalier = 3;
        public static bool Monte(int a) => a == Cavalier;
        // Un destrier de 520 kg et un homme d'armes de 100 kg ; sans masse (contre-épreuve), un cheval pèse un homme.
        public static float Masse(int a, byte masse) => Monte(a) && masse != 0 ? 620f : 80f;
        public static float ForceMax(int a, byte masse) => Monte(a) && masse != 0 ? 3000f : 400f;
        // Un cheval est un corps long : on l'approche par un disque de 1,3 m, un homme par un disque de 0,8 m.
        public static float Rayon(int a) => Monte(a) ? 0.65f : 0.4f;
        public static float Taille(int a) => Monte(a) ? 2.3f : 1.75f;
        public static float VitesseMax(int a) => Monte(a) ? 8.5f : 2.6f;     // le galop de charge ; le pas de course
        public static float VitesseFuite(int a) => Monte(a) ? 7f : 3.2f;
    }

    // L'état d'animation lu par le shader du soldat, instance par instance :
    // x phase de marche (0..1), y poids de la marche, z décalage du repos.
    [MaterialProperty("_AnimEtat")]
    public struct AnimEtat : IComponentData
    {
        public float4 Value;
    }

    // L'ordre donné à des hommes : un point, une direction, une largeur de front.
    public struct Regiment : IComponentData
    {
        public float2 Position;      // l'ancre de la formation, qui avance vers la cible
        public float2 Cible;
        public float2 Front;         // direction vers laquelle la formation fait face (unitaire)
        public float2 FrontCible;
        public float2 Base, Avant;   // les deux lignes du scénario de démonstration
        public float VitesseMarche;
        public float Espacement;
        public float Attente;
        public float Ecart;          // écart moyen de ses hommes à leur place
        public int Files;            // largeur du front, en hommes
        public int Effectif;
        public int Index;
        public int Arme;             // 0 piquiers, 1 hallebardiers, 2 arbalétriers, 3 cavaliers
        public int Camp;
        public int Etape;
        public byte Ordonne;         // 1 : le joueur a pris la main, le scénario s'arrête
        public byte Selection;
        public Entity Ennemi;        // le régiment qu'on a ordre d'attaquer
        public int Contacts;         // hommes au contact de l'ennemi, à la dernière image
        public float Melee;          // secondes restantes dans l'état de mêlée (les rangs s'appuient)
        public float2 CentreHommes;  // où se tiennent réellement ses hommes
        public float Fuyards;        // part de ses hommes qui fuient
        public byte Deroute;         // 1 : la moitié de ses hommes fuient ; il ne combat plus
        public byte Tir;             // 1 : arbalétriers à portée de leur cible, arrêtés, qui tirent
        public byte SansPavois;      // pour les essais : ce régiment n'a pas de pavois
        public int Touches;          // coups et carreaux reçus par ses hommes
        public byte Herisse;         // 1 : un ennemi approche de front ; les piquiers baissent leurs piques
        public float2 Vitesse;       // m/s : l'allure de l'ancre, à la dernière image

        public int Rangs => (Effectif + Files - 1) / Files;
        // Les dimensions suivent l'espacement réel : serré dans la mêlée, ouvert sinon.
        public float Largeur => (math.min(Files, Effectif) - 1) * Formation.Pas(this).x;
        public float Profondeur => (Rangs - 1) * Formation.Pas(this).y;
    }

    // Réglages de la simulation, pour les contre-épreuves des essais, jamais des réglages de jeu.
    // Corps = 0 retire la gêne entre les hommes ; Poussee = 0 retire la poussée de charge des
    // rangs arrière (seuls les hommes au contact de l'ennemi appuient ; les autres tiennent leur place).
    public struct ReglagesSimulation : IComponentData
    {
        public byte Corps;
        public byte Poussee;
        public byte Peur;        // 0 : personne n'a peur (contre-épreuve du jalon 5, isolement du jalon 4)
        public byte Pavois;      // 0 : aucun pavois n'arrête rien (contre-épreuve du jalon 6)
        public byte Masse;       // 0 : un cheval pèse et pousse comme un homme (contre-épreuve du jalon 7)
        public byte Piques;      // 0 : les piques baissées n'arrêtent pas les chevaux (contre-épreuve du jalon 7)
    }

    public static class Formation
    {
        // Place d'un homme dans le repère du régiment : x vers la droite, y vers l'avant.
        // Le dernier rang, incomplet, se centre derrière les autres.
        public const float EspacementSerre = 0.8f, ProfondeurSerree = 0.9f;   // épaule contre épaule
        // Les cavaliers chargent botte à botte, un cheval et demi entre deux rangs.
        public const float EspacementCavalier = 1.5f, ProfondeurCavalier = 3.4f;

        // L'écart entre deux files et entre deux rangs. Dans la mêlée, les rangs à pied se serrent :
        // épaule contre épaule, sans vide où l'ennemi se glisse. Des chevaux ne se serrent pas.
        public static float2 Pas(in Regiment r) =>
            Corps.Monte(r.Arme) ? new float2(EspacementCavalier, ProfondeurCavalier)
            : r.Melee > 0 ? new float2(EspacementSerre, ProfondeurSerree) : new float2(r.Espacement, r.Espacement);

        public static float2 Place(in Regiment r, int numero)
        {
            int files = math.max(1, math.min(r.Files, r.Effectif));
            int rangs = (r.Effectif + files - 1) / files;
            int rg = numero / files, f = numero % files;
            int dansLeRang = rg == rangs - 1 ? r.Effectif - rg * files : files;
            float2 pas = Pas(r);
            float ex = pas.x, ey = pas.y;
            // Les arbalétriers se forment en quinconce : chaque rang tire dans l'intervalle de celui de devant.
            float quinconce = r.Arme == 2 && r.Melee <= 0 ? ((rg & 1) - 0.5f) * 0.5f * ex : 0f;
            return new float2((f - (dansLeRang - 1) / 2f) * ex + quinconce, -(rg - (rangs - 1) / 2f) * ey);
        }

        public static float2 VersMonde(float2 local, float2 ancre, float2 front)
        {
            float2 droite = new float2(front.y, -front.x);
            return ancre + droite * local.x + front * local.y;
        }
    }

    // Le relief lu une fois depuis le Terrain, pour poser les pieds dans les jobs Burst.
    public struct ReliefBlob
    {
        public BlobArray<float> Hauteurs; // [z * Resolution + x], en mètres
        public int Resolution;
        public float Taille;
        public float3 Origine;
    }

    public struct Relief : IComponentData
    {
        public BlobAssetReference<ReliefBlob> Blob;
    }

    public static class Sol
    {
        // Le Terrain de Unity découpe chaque maille le long de la diagonale
        // (i,j)–(i+1,j+1) : on suit le même découpage pour que les pieds
        // touchent exactement la surface dessinée.
        public static float Hauteur(ref ReliefBlob r, float2 p)
        {
            int n = r.Resolution;
            float2 uv = (p - r.Origine.xz) / r.Taille * (n - 1);
            uv = math.clamp(uv, 0f, n - 1.0001f);
            int2 i = (int2)math.floor(uv);
            float2 f = uv - i;
            float h00 = r.Hauteurs[i.y * n + i.x];
            float h10 = r.Hauteurs[i.y * n + i.x + 1];
            float h01 = r.Hauteurs[(i.y + 1) * n + i.x];
            float h11 = r.Hauteurs[(i.y + 1) * n + i.x + 1];
            float h = f.x >= f.y
                ? h00 + (h10 - h00) * f.x + (h11 - h10) * f.y
                : h00 + (h11 - h01) * f.x + (h01 - h00) * f.y;
            return r.Origine.y + h;
        }
    }
}
