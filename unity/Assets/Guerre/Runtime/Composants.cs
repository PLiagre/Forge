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
        public static float Portee(int a) => a == 0 ? 3.2f : a == 1 ? 1.9f : 1.1f;   // pique, hallebarde, dague
        public static float Cadence(int a) => a == 0 ? 3.2f : a == 1 ? 3.8f : 2.4f;  // secondes entre deux coups
        public static float Degats(int a) => a == 0 ? 0.22f : a == 1 ? 0.4f : 0.18f;
        public static float Armure(int a) => a == 0 ? 0.15f : a == 1 ? 0.45f : 0.05f; // part du coup arrêtée
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
        public int Arme;             // 0 piquiers, 1 hallebardiers, 2 arbalétriers
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

        public int Rangs => (Effectif + Files - 1) / Files;
        // Les dimensions suivent l'espacement réel : serré dans la mêlée, ouvert sinon.
        public float Largeur => (math.min(Files, Effectif) - 1) * (Melee > 0 ? Formation.EspacementSerre : Espacement);
        public float Profondeur => (Rangs - 1) * (Melee > 0 ? Formation.ProfondeurSerree : Espacement);
    }

    // Réglages de la simulation, pour les contre-épreuves des essais, jamais des réglages de jeu.
    // Corps = 0 retire la gêne entre les hommes ; Poussee = 0 retire la poussée de charge des
    // rangs arrière (seuls les hommes au contact de l'ennemi appuient ; les autres tiennent leur place).
    public struct ReglagesSimulation : IComponentData
    {
        public byte Corps;
        public byte Poussee;
        public byte Peur;        // 0 : personne n'a peur (contre-épreuve du jalon 5, isolement du jalon 4)
    }

    public static class Formation
    {
        // Place d'un homme dans le repère du régiment : x vers la droite, y vers l'avant.
        // Le dernier rang, incomplet, se centre derrière les autres.
        public const float EspacementSerre = 0.8f, ProfondeurSerree = 0.9f;   // épaule contre épaule

        public static float2 Place(in Regiment r, int numero)
        {
            int files = math.max(1, math.min(r.Files, r.Effectif));
            int rangs = (r.Effectif + files - 1) / files;
            int rg = numero / files, f = numero % files;
            int dansLeRang = rg == rangs - 1 ? r.Effectif - rg * files : files;
            // Dans la mêlée, les rangs se serrent : épaule contre épaule, sans vide où l'ennemi se glisse.
            float ex = r.Melee > 0 ? EspacementSerre : r.Espacement, ey = r.Melee > 0 ? ProfondeurSerree : r.Espacement;
            return new float2((f - (dansLeRang - 1) / 2f) * ex, -(rg - (rangs - 1) / 2f) * ey);
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
