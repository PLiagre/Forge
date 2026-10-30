using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Le geste du joueur (lot 263) : clic gauche pose un point sur le terrain, Entrée trace la
    // route, Échap annule. Le clic ne fait que convertir un point d'écran en point du terrain.
    // Lot 293 : la route n'est plus posée par l'outil. Il l'essaie sur le relief (DesertRoads.Poser
    // en essai, qui refuse la route trop raide), la dépose au monde comme intention `tracer_route`,
    // puis dessine au tick suivant les rues neuves que `/plan` publie. Toute route en chantier est
    // en terre battue. Le panneau est un texte posé devant la caméra : il apparaît aussi dans les
    // captures.
    // Lot 361 : au lancement, l'outil lit le plan de sa cellule et pose toutes ses rues, dans l'ordre
    // du plan, sur une copie vierge du terrain. Une rue que le relief refuse reste au plan : le panneau
    // la déclare par son identifiant. Unity ne garde aucun plan à lui : relancé, il redessine la même ville.
    // Lot 362 : après les rues, l'outil trace au sol chaque parcelle du plan (DesertParcelles) : cordeau
    // en chantier, bornes achevée. Il les redessine toutes à l'ouverture, après une route et par Rafraichir.
    // Lot 369 : après les parcelles, la pièce du kit à l'étape de chaque bâtiment du plan (DesertBatiments).
    // Lot 375 : P passe en mode parcelle. Deux coins posés le long d'une rue, Entrée calcule la parcelle
    // (TraceDeParcelle) et dépose `decouper_parcelle` au monde ; Attendre la dessine au tick suivant. Un refus
    // de l'outil n'atteint jamais le monde ; celui du monde s'affiche avec sa raison. Échap ramène aux routes.
    // Lot 377 : 1, 2, 3 passent en mode bâtiment (maison, scierie, four). Un clic sur une parcelle forme la pose
    // (PoseDeBatiment) et dépose `poser_batiment` au monde ; Attendre dessine la pièce au tick suivant.
    // Lot 584 : Ouvrir(cellule) ouvre la ville d'une autre cellule, celle des lectures et des dépôts suivants, sur le
    // même service local ; rien de l'ancienne cellule (points, mode, reçu, dépôt en attente, relevés de pose) ne la suit.
    // Lot 688 : au lancement, Lancer applique la décision de #687 : la cellule du siège du joueur, la carte de 1400, ou l'absence.
    // Lot 730 : C revient à la carte, Espace suspend ou reprend. Le clavier reste ici ; le pont n'en a pas.
    // Lot 907 : après les maisons, l'enceinte du plan (DesertEnceinte), tours, pans et porte à l'étape du chantier.
    public sealed class DesertRoadTool : MonoBehaviour
    {
        public DesertRoads roads;public Camera view;
        public const string Revetement="terre";public double largeur=4;
        // Piloté par le contrôle : ni souris ni clavier, et Attendre appelé par lui.
        public bool automatique;
        public Mesh maillageCivil;public Material materiauCivil;PassantsDeLaVille passants; // VAT de #786, les deux scènes de ville.
        readonly List<(double x,double y)> points=new();
        public (double x,double y)[] Derniers{get;private set;}=new (double,double)[0];
        public string Message{get;private set;}="";
        // Le service du monde : la cellule lue sur la ligne de commande, le port du service local.
        public long Cellule{get;private set;}=-1;public int Port{get;private set;}=-1;
        // Le reçu du dernier dépôt ; null tant que rien n'est déposé.
        public RecuIntention Recu{get;private set;}
        // Les rues neuves du plan dessinées par Attendre : identifiant et résultat de la pose.
        public readonly List<(long identifiant,DesertRoads.Resultat resultat)> Posees=new();
        // Lot 361 : chaque rue essayée à l'ouverture, dans l'ordre du plan, acceptée ou refusée ;
        // le tick du plan lu à l'ouverture, -1 tant qu'aucun ne l'a été.
        public readonly List<(long identifiant,DesertRoads.Resultat resultat)> Ouverture=new();
        public long TickOuverture{get;private set;}=-1;
        // Lot 362 : le dernier dessin des parcelles, dans l'ordre du plan (cordeau, bornes ou refusee).
        public readonly List<(long identifiant,string etat,string message)> Parcelles=new();
        public Transform RacineParcelles=>parcelles?.Racine;
        public string EmpreinteParcelles=>parcelles?.Empreinte??"";
        DesertParcelles parcelles;string erreurParcelles;
        // Lot 369 : le dernier dessin des bâtiments, dans l'ordre du plan (piquets, murs, fini ou refusee).
        public readonly List<(long identifiant,string etat,string message)> Batiments=new();
        public Transform RacineBatiments=>batiments?.Racine;
        public string EmpreinteBatiments=>batiments?.Empreinte??"";
        DesertBatiments batiments;string erreurBatiments;
        DesertEnceinte enceinte;string erreurEnceinte;
        public DesertEnceinte Enceinte=>enceinte;
        // Lot 737 : les maisons de la base, jamais mêlées aux bâtiments de geste.
        DesertMaisons1400 maisons;
        public DesertMaisons1400 Maisons=>maisons;
        // Lot 738 : les rues de la base en rubans posés sur le sable, redessinés avec les maisons, juste avant elles.
        DesertRues1400 rues1400;public DesertRues1400 Rues1400=>rues1400;
        public int PiecesAvantMaisons{get;private set;}=-1;
        public string EmpreinteAvantMaisons{get;private set;}="";
        ClientIntention depot;ClientPlan plan;string erreurCellule;
        LectureCarte carte;bool carteLue;string reliefOuvert;
        // Les rues déjà essayées dans la session, posées ou refusées : aucune n'est posée deux fois, ni réessayée.
        readonly HashSet<long> essayees=new();
        RecuIntention enAttente;double prochaineLecture;
        TextMesh panneau,halo;
        // Lot 375 : le mode parcelle, et le dernier calcul de l'outil (null tant qu'aucun n'a été fait).
        public bool ModeParcelle{get;private set;}
        public ParcelleTracee Tracee{get;private set;}
        // Lot 377 : la nature choisie (null hors du mode bâtiment), et le dernier calcul de pose (null tant qu'aucun n'a été fait).
        public string NatureBatiment{get;private set;}
        public bool ModeBatiment=>NatureBatiment!=null;
        public BatimentPose Pose{get;private set;}
        CommandesDeVille commandes;
        const string Aide="Clic : poser un point · Entrée : tracer la route · Échap : annuler · P : parcelle · 1, 2, 3 : bâtiment";
        const string AideParcelle="Clic : poser deux coins le long d'une rue · Entrée : déposer la parcelle · Échap : annuler";
        const string AideBatiment="Clic : poser sur une parcelle · 1 : maison · 2 : scierie · 3 : four · Échap : annuler";
        const string Gestes="C : carte · Espace : pause / reprendre";
        const double PeriodeLecture=.25;
        static readonly TimeSpan Delai=TimeSpan.FromSeconds(1);
        // Lot 688 : l'aiguillage du lancement lit /monde puis /maison ; les gestes gardent leur délai.
        static readonly TimeSpan DelaiAiguillage=TimeSpan.FromSeconds(5);
        const string CarteOuverte="La carte de 1400 s'ouvre : aucune capitale à ouvrir ici.";

        void Awake()
        {
            var font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            TextMesh Texte(string nom,Transform parent,Color couleur)
            {
                var go=new GameObject(nom);go.transform.SetParent(parent,false);
                var t=go.AddComponent<TextMesh>();t.font=font;go.GetComponent<MeshRenderer>().sharedMaterial=font.material;
                t.fontSize=64;t.anchor=TextAnchor.LowerLeft;t.color=couleur;return t;
            }
            panneau=Texte("Panneau des routes",view.transform,new Color(.12f,.06f,.03f));
            // Un halo clair derrière le texte : il reste lisible sur le sable comme dans l'ombre.
            halo=Texte("Halo",panneau.transform,new Color(1f,.95f,.84f,.9f));
            Port=PanneauLieu.DEFAULT_SERVICE_PORT;commandes=new CommandesDeVille(Port);
            // Lot 701 : une ville ouverte depuis la carte prend la cellule que le passage a remise à sa scène.
            Lancer(Environment.GetCommandLineArgs(),Application.isEditor,FindFirstObjectByType<PanneauLieu>(),PassageALaCapitale.PrendreCelluleRemise(gameObject.scene.name));
            // Sans matériau, aucune parcelle n'est jamais dessinée : le panneau le dit.
            try{parcelles=new DesertParcelles(transform,roads.terrain);}
            catch(InvalidOperationException e){erreurParcelles=e.Message;}
            // Sans kit, aucun bâtiment n'est jamais dessiné : le panneau le dit.
            try{batiments=new DesertBatiments(transform,roads.terrain);}
            catch(InvalidOperationException e){erreurBatiments=e.Message;}
            try{enceinte=new DesertEnceinte(transform,roads.terrain,KitDesBatiments.Charger());}
            catch(InvalidOperationException e){erreurEnceinte=e.Message;}
            rues1400=new DesertRues1400(transform,roads.terrain,roads.terreBattue);maisons=new DesertMaisons1400(transform,roads.terrain);
            passants=gameObject.AddComponent<PassantsDeLaVille>();passants.Brancher(maillageCivil,materiauCivil,roads.terrain,this);
            Afficher(erreurCellule??erreurParcelles??erreurBatiments??Aide);
        }
        void Start()=>Ouvrir();

        // Lot 688 : applique la décision du lancement (OuvertureDeLaCapitale, #687), puis la rend. En ville, la cellule est
        // celle des lectures et des dépôts, et le panneau du lieu la suit ; aucun plan n'est lu ici, Ouvrir() le dessine.
        // Sinon, aucune cellule : l'absence garde sa cause mot pour mot, et le panneau du lieu s'éteint sans rien lire.
        // Le panneau peut manquer (la scène de l'oued n'en a pas).
        public Lecture<OuvertureDecidee> Lancer(string[] arguments,bool editeur,PanneauLieu panneau,long? remise=null)
        {
            carteLue=false;carte=null;
            var decision=OuvertureDeLaCapitale.Decider(arguments,editeur,remise,()=>AiguillageDeCapitale.Lire(Port,DelaiAiguillage));
            var mode=decision.Presente?decision.Donnees.Mode:(ModeDOuverture?)null;
            if(mode==ModeDOuverture.Ville)
            {
                Cellule=decision.Donnees.Cellule.Value;erreurCellule=null;
                plan??=new ClientPlan(Port,Delai);depot??=new ClientIntention(Port,Delai);
                if(panneau)panneau.Ouvrir(Cellule);
                return decision;
            }
            Cellule=-1;erreurCellule=mode==null?decision.Absence:CarteOuverte;
            if(panneau)panneau.enabled=false;
            // LaisseeALaCarte : OuvertureDeLaCarte change déjà de scène.
            if(mode==ModeDOuverture.Carte)SceneManager.LoadScene(decision.Donnees.Scene);
            return decision;
        }
        void OnDestroy(){depot?.Dispose();plan?.Dispose();depot=null;plan=null;}
        void Afficher(string texte)
        {
            Message=texte;
            // Lot 375 : en mode parcelle, l'aide du mode suit toujours l'état, sous le message s'il y en a un.
            if(ModeParcelle)
                panneau.text=(texte==AideParcelle?"":texte+"\n")+"Parcelle le long d'une rue · "+points.Count+"/2 coin(s)\n"+AideParcelle;
            // Lot 377 : de même en mode bâtiment.
            else if(ModeBatiment)
                panneau.text=(texte==AideBatiment?"":texte+"\n")+"Bâtiment : "+NatureBatiment+" · un clic sur une parcelle\n"+AideBatiment;
            else
            {
                string etat="Terre battue, "+largeur.ToString("0.#")+" m"+(points.Count>0?" · "+points.Count+" point(s)":"");
                panneau.text=texte==Aide?etat+"\n"+Aide:texte+"\n"+etat;
            }
            if(reliefOuvert!=null)panneau.text+="\nRelief : "+reliefOuvert;
            panneau.text+="\n"+Gestes;
            halo.text=panneau.text;
            Placer();
        }
        // En bas à gauche de l'image, à hauteur de lecture quelle que soit la focale.
        public void Placer()
        {
            if(!panneau)return;
            float d=view.nearClipPlane+.5f,h=2*d*Mathf.Tan(view.fieldOfView*Mathf.Deg2Rad/2),w=h*view.aspect;
            var t=panneau.transform;t.localRotation=Quaternion.identity;t.localScale=Vector3.one;panneau.characterSize=1;
            var r=panneau.GetComponent<MeshRenderer>();float lignes=Mathf.Max(1,panneau.text.Count(c=>c=='\n')+1);
            float ligne=r.localBounds.size.y/lignes;
            if(ligne>0)t.localScale=Vector3.one*(h/32/ligne);
            halo.transform.localPosition=new Vector3(ligne*.06f,-ligne*.06f,ligne*.05f);
            t.localPosition=new Vector3(-w/2+h*.03f,-h/2+h*.04f,d);
        }

        void Update()
        {
            if(automatique)return;
            if(enAttente!=null&&Time.realtimeSinceStartupAsDouble>=prochaineLecture)
            {prochaineLecture=Time.realtimeSinceStartupAsDouble+PeriodeLecture;Attendre();}
            var mouse=Mouse.current;var k=Keyboard.current;
            if(mouse!=null&&mouse.leftButton.wasPressedThisFrame)Clic(mouse.position.ReadValue());
            if(k==null)return;
            if(k.pKey.wasPressedThisFrame)EntrerParcelle();
            // Les chiffres suivent la position physique : sur un clavier AZERTY, la touche « & 1 », sans Maj.
            if(k.digit1Key.wasPressedThisFrame||k.numpad1Key.wasPressedThisFrame)EntrerBatiment(PoseDeBatiment.Natures[0]);
            if(k.digit2Key.wasPressedThisFrame||k.numpad2Key.wasPressedThisFrame)EntrerBatiment(PoseDeBatiment.Natures[1]);
            if(k.digit3Key.wasPressedThisFrame||k.numpad3Key.wasPressedThisFrame)EntrerBatiment(PoseDeBatiment.Natures[2]);
            if(k.enterKey.wasPressedThisFrame||k.numpadEnterKey.wasPressedThisFrame){if(ModeParcelle)ValiderParcelle();else if(!ModeBatiment)Valider();}
            if(k.escapeKey.wasPressedThisFrame)Annuler();
            if(k.cKey.wasPressedThisFrame||commandes.RetourDemande)commandes.Retour();
            if(k.spaceKey.wasPressedThisFrame)commandes.Basculer();
        }
        void LateUpdate()=>Placer();

        public bool Clic(Vector2 ecran)
        {
            var ray=view.ScreenPointToRay(ecran);
            if(!roads.terrain.GetComponent<TerrainCollider>().Raycast(ray,out var hit,10000)){Afficher("Ce point n'est pas sur le terrain.");return false;}
            // Lot 377 : en mode bâtiment, le point désigne la parcelle ; il ne s'ajoute pas aux points.
            if(ModeBatiment){var (x,y)=roads.PointExact(hit.point);PoserBatiment(x,y);return true;}
            if(ModeParcelle&&points.Count>=2){Afficher("Deux coins suffisent : Entrée pour déposer, Échap pour annuler.");return false;}
            points.Add(roads.PointExact(hit.point));Afficher(ModeParcelle?AideParcelle:Aide);return true;
        }
        public void Annuler(){ModeParcelle=false;NatureBatiment=null;points.Clear();Recu=null;Afficher(Aide);}

        // Lot 375 : le mode parcelle, coins effacés. Échap (Annuler) ramène au mode route.
        public void EntrerParcelle(){points.Clear();Recu=null;Tracee=null;ModeParcelle=true;NatureBatiment=null;Afficher(AideParcelle);}

        // Lot 377 : le mode bâtiment, pour la nature choisie. Elle n'est pas jugée ici : Calculer le fait au clic.
        public void EntrerBatiment(string nature){points.Clear();Recu=null;Pose=null;ModeParcelle=false;NatureBatiment=nature;Afficher(AideBatiment);}

        // Lot 375 : calcule la parcelle des deux coins, puis la dépose au monde, qui reste le seul juge.
        // Le terrain ne bouge pas ici : la parcelle se dessine dans Attendre, d'après le plan du tick suivant.
        // Rend le calcul de l'outil, null hors du mode parcelle ou faute de coins, de cellule ou de plan.
        public ParcelleTracee ValiderParcelle()
        {
            if(!ModeParcelle)return null;
            if(points.Count<2){Afficher("Il faut deux coins.");return null;}
            Recu=null;
            var (x1,y1)=points[0];var (x2,y2)=points[1];points.Clear();
            if(erreurCellule!=null){Afficher(erreurCellule);return null;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan : "+lu.Absence);return null;}
            Tracee=TraceDeParcelle.Calculer(lu.Plan,new PointLocal(x1,y1),new PointLocal(x2,y2));
            // Une parcelle que l'outil refuse n'atteint jamais le monde.
            if(!Tracee.Presente){Afficher("Parcelle refusée par l'outil : "+Tracee.Absence);return Tracee;}
            Recu=depot.Deposer(Tracee.IntentionJson);
            if(Recu.Acceptee)
            {
                enAttente=Recu;
                Afficher("Parcelle déposée au monde : elle se dessine au tick suivant (après le tick "+Recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture)+").");
            }
            else Afficher(Recu.Presente?"Le monde refuse la parcelle : "+Recu.Erreur:"Pas de reçu : "+Recu.Absence);
            return Tracee;
        }

        // Lot 377 : forme la pose sur la parcelle sous le point, puis la dépose au monde, qui reste le seul juge
        // (« parcelle déjà bâtie » est son refus, pas celui de l'outil). La pièce se dessine dans Attendre, au
        // tick suivant. L'outil reste en mode bâtiment, avec la même nature.
        void PoserBatiment(double x,double y)
        {
            Recu=null;Pose=null;
            if(erreurCellule!=null){Afficher(erreurCellule);return;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan : "+lu.Absence);return;}
            Pose=PoseDeBatiment.Calculer(lu.Plan,new PointLocal(x,y),NatureBatiment);
            // Une pose que l'outil refuse n'atteint jamais le monde.
            if(!Pose.Presente){Afficher("Bâtiment refusé par l'outil : "+Pose.Absence);return;}
            Recu=depot.Deposer(Pose.IntentionJson);
            if(Recu.Acceptee)
            {
                enAttente=Recu;
                Afficher("Bâtiment déposé au monde : "+Pose.Nature+" sur la parcelle "+Pose.Parcelle.ToString(CultureInfo.InvariantCulture)
                    +", dessiné au tick suivant (après le tick "+Recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture)+").");
            }
            else Afficher(Recu.Presente?"Le monde refuse le bâtiment : "+Recu.Erreur:"Pas de reçu : "+Recu.Absence);
        }

        // Essaie la route sur le relief, puis la dépose au monde. Le terrain ne bouge pas ici :
        // la route se dessine dans Attendre, d'après le plan du tick suivant. Rend le résultat de l'essai.
        public DesertRoads.Resultat Valider()
        {
            if(points.Count<2){Afficher("Il faut au moins deux points.");return null;}
            Recu=null;Posees.Clear();
            var g=new DesertRoads.Geste{id="joueur",revetement=Revetement,largeur=largeur,x=points.Select(p=>p.x).ToArray(),y=points.Select(p=>p.y).ToArray()};
            Derniers=points.ToArray();points.Clear();
            var r=roads.Poser(g,essai:true);
            // Une route que le relief refuse n'atteint jamais le monde.
            if(!r.acceptee){Afficher(r.message);return r;}
            if(erreurCellule!=null){Afficher(erreurCellule);return r;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan : "+lu.Absence);return r;}
            Recu=depot.Deposer(Intention(g));
            if(Recu.Acceptee)
            {
                enAttente=Recu;
                Afficher("Route déposée au monde : elle se trace au tick suivant (après le tick "+Recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture)+").");
            }
            else Afficher(Recu.Presente?"Le monde refuse la route : "+Recu.Erreur:"Pas de reçu : "+Recu.Absence);
            return r;
        }

        // Formée à la main : les nombres en culture invariante, au format "R" (aller-retour exact).
        // Publique (lot 361) : le contrôle du relancement et la capture forment leurs dépôts avec elle.
        public string Intention(DesertRoads.Geste g)
        {
            string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
            var s=new StringBuilder("{\"type\":\"tracer_route\",\"cell\":").Append(Cellule.ToString(CultureInfo.InvariantCulture)).Append(",\"points\":[");
            for(int i=0;i<g.x.Length;i++)s.Append(i>0?",":"").Append('[').Append(N(g.x[i])).Append(',').Append(N(g.y[i])).Append(']');
            return s.Append("],\"largeur_m\":").Append(N(g.largeur)).Append('}').ToString();
        }

        // Après le tick qui a appliqué le dépôt, dessine chaque rue du plan encore jamais essayée,
        // de tout auteur, dans l'ordre du plan. Faux tant que ce tick n'est pas publié.
        public bool Attendre()
        {
            if(enAttente==null||plan==null)return false;
            var lu=plan.Lire(Cellule);
            if(!lu.Presente||lu.Plan.Tick<=enAttente.AppliqueeAuTick.Value)return false;
            var essais=Dessiner(lu.Plan);Posees.AddRange(essais);
            // Une rue neuve a pu changer le sol sous les parcelles : toutes sont redessinées.
            Afficher(Bilan("Après le tick "+lu.Plan.Tick.ToString(CultureInfo.InvariantCulture)+" : "+essais.Count(e=>e.resultat.acceptee)+" rue(s) neuve(s) posée(s).",essais)
                +"\n"+DessinerParcelles(lu.Plan)+"\n"+DessinerBatiments(lu.Plan));
            enAttente=null;
            return true;
        }

        // Lot 361 : la ville d'après le plan, sur une copie vierge du terrain. Appelée au lancement ;
        // un dépôt en attente n'est pas touché. Faux, terrain inchangé, si la cellule, le plan ou les
        // paramètres des routes manquent : l'absence est affichée, jamais devinée.
        public bool Ouvrir()
        {
            if(erreurCellule!=null){Afficher(erreurCellule);return false;}
            if(!PreparerOuverture(Cellule,"Pas de plan à l'ouverture : ",false))return false;
            return true;
        }

        // Lot 584 : la ville d'une autre cellule, sur une copie vierge du terrain, par le dessin d'Ouvrir(). Le port reste
        // celui du service local. Faux, sans rien changer ni dessiner, si la cellule est invalide, son plan absent ou les
        // paramètres des routes manquants : l'absence est affichée, jamais remplacée par un plan de secours.
        public bool Ouvrir(long cellule)
        {
            string c=cellule.ToString(CultureInfo.InvariantCulture);
            if(cellule<0){Afficher("Cellule "+c+" invalide : un cell_id entier positif ou nul attendu.");return false;}
            plan??=new ClientPlan(Port,Delai);depot??=new ClientIntention(Port,Delai);
            if(!PreparerOuverture(cellule,"Pas de plan pour la cellule "+c+" : ",true))return false;
            return true;
        }

        // Carte, relief, plan et paramètres avant la remise à zéro : un refus garde la ville précédente.
        bool PreparerOuverture(long cellule,string prefixePlan,bool changer)
        {
            string c=cellule.ToString(CultureInfo.InvariantCulture);
            if(!carteLue){using(var client=new ClientCarte(Port,ClientCarte.DelaiMinimal))carte=client.Lire();carteLue=true;}
            if(carte==null||!carte.Presente){Afficher("Cellule "+c+" : carte indisponible : "+(carte==null?"lecture absente":carte.Absence));return false;}
            var cell=carte.Carte.Cellules.FirstOrDefault(x=>x.CellId==cellule);
            if(cell==null){Afficher("Cellule "+c+" absente de la carte.");return false;}
            if(string.IsNullOrEmpty(cell.Relief)){Afficher("Cellule "+c+" : relief absent.");return false;}
            var lu=plan.Lire(cellule);
            if(!lu.Presente){Afficher(prefixePlan+lu.Absence);return false;}
            if(!LireParametres(out var parametres))return false;
            if(!roads.ResoudreRelief(parametres.parametres,cell.Relief,out var facteur,out var cause)){Afficher("Cellule "+c+" : "+cause);return false;}
            if(changer){if(cellule!=Cellule)passants?.Retirer();Cellule=cellule;erreurCellule=null;points.Clear();ModeParcelle=false;NatureBatiment=null;Recu=null;enAttente=null;Posees.Clear();Derniers=new (double,double)[0];Tracee=null;Pose=null;}
            Ouverture.Clear();essayees.Clear();TickOuverture=-1;
            roads.AppliquerRelief(facteur,cell.Relief);reliefOuvert=cell.Relief;
            DessinerOuverture(lu.Plan,parametres);
            return true;
        }

        bool LireParametres(out DesertRoads.Gestes parametres)
        {
            try{parametres=DesertRoads.Lire(roads.implantation);return true;}
            catch(InvalidOperationException e){parametres=null;Afficher(e.Message);return false;}
        }

        void DessinerOuverture(PlanLu lu,DesertRoads.Gestes parametres)
        {
            roads.Preparer(parametres.parametres,parametres.graine);
            Ouverture.AddRange(Dessiner(lu));TickOuverture=lu.Tick;
            // Les parcelles après les rues : leur sol est celui de la copie où les rues sont posées.
            Afficher(Bilan("Plan du tick "+TickOuverture.ToString(CultureInfo.InvariantCulture)+" : "+Ouverture.Count(e=>e.resultat.acceptee)+" rue(s) posée(s).",Ouverture)
                +"\n"+DessinerParcelles(lu)+"\n"+DessinerBatiments(lu));
        }

        // Lot 362 : relit le plan et redessine ses parcelles, sans toucher aux rues. Faux, parcelles
        // inchangées, si la cellule est en erreur ou le plan absent. Jamais appelée périodiquement.
        public bool Rafraichir()
        {
            if(erreurCellule!=null){Afficher(erreurCellule);return false;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan : "+lu.Absence);return false;}
            Afficher("Plan du tick "+lu.Plan.Tick.ToString(CultureInfo.InvariantCulture)+" : "+DessinerParcelles(lu.Plan)+"\n"+DessinerBatiments(lu.Plan));
            return true;
        }

        // Remplace Parcelles par le dessin du plan. Rend la ligne du panneau, puis une ligne par parcelle refusée.
        string DessinerParcelles(PlanLu lu)
        {
            if(parcelles==null)return erreurParcelles;
            Parcelles.Clear();Parcelles.AddRange(parcelles.Dessiner(lu.Parcelles));
            return string.Join("\n",new[]{"Parcelles : "+Parcelles.Count(p=>p.etat=="cordeau")+" en chantier, "+Parcelles.Count(p=>p.etat=="bornes")+" achevée(s)."}
                .Concat(Parcelles.Where(p=>p.etat=="refusee").Select(p=>p.message)));
        }

        // Lot 369 : remplace Batiments par le dessin du plan, après les parcelles (sur le sol où les rues sont
        // posées). Rend la ligne du panneau, puis une ligne par bâtiment refusé.
        string DessinerBatiments(PlanLu lu)
        {
            if(batiments==null)return erreurBatiments;
            Batiments.Clear();Batiments.AddRange(batiments.Dessiner(lu.Batiments));
            PiecesAvantMaisons=batiments.Racine.childCount;EmpreinteAvantMaisons=batiments.Empreinte;
            string rendu=string.Join("\n",new[]{"Bâtiments : "+Batiments.Count(b=>b.etat=="piquets")+" aux piquets, "+Batiments.Count(b=>b.etat=="murs")+" aux murs, "+Batiments.Count(b=>b.etat=="fini")+" fini(s)."}
                .Concat(Batiments.Where(b=>b.etat=="refusee").Select(b=>b.message)))+"\n"+rues1400.Dessiner(lu.Base)+"\n"+maisons.Dessiner(lu.Base);
            string mur=enceinte!=null?enceinte.Dessiner(lu.Enceinte,lu.Portes):lu.Enceinte!=null?erreurEnceinte:"";
            return string.IsNullOrEmpty(mur)?rendu:rendu+"\n"+mur;
        }

        // Pose en terre battue, dans l'ordre du plan, chaque rue jamais essayée dans la session, aux
        // points et à la largeur du plan. Rend ce qu'elle a essayé, posé ou refusé.
        List<(long identifiant,DesertRoads.Resultat resultat)> Dessiner(PlanLu lu)
        {
            var essais=new List<(long identifiant,DesertRoads.Resultat resultat)>();
            foreach(var rue in lu.Rues.Where(u=>!essayees.Contains(u.Identifiant)))
            {
                var r=roads.Poser(new DesertRoads.Geste{id="plan_"+rue.Identifiant.ToString(CultureInfo.InvariantCulture),revetement=Revetement,largeur=rue.LargeurM,
                    x=rue.Points.Select(p=>p.X).ToArray(),y=rue.Points.Select(p=>p.Y).ToArray()});
                essayees.Add(rue.Identifiant);essais.Add((rue.Identifiant,r));
            }
            return essais;
        }

        // La ligne de tête, puis une ligne par rue que le relief refuse : elle reste au plan, l'écran la nomme.
        static string Bilan(string tete,IEnumerable<(long identifiant,DesertRoads.Resultat resultat)> essais)
            =>string.Join("\n",new[]{tete}.Concat(essais.Where(e=>!e.resultat.acceptee)
                .Select(e=>"Rue "+e.identifiant.ToString(CultureInfo.InvariantCulture)+" refusée par le relief : "+e.resultat.message)));
    }
}
