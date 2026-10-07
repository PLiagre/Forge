using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;

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
    public sealed class DesertRoadTool : MonoBehaviour
    {
        public DesertRoads roads;public Camera view;
        public const string Revetement="terre";public double largeur=4;
        // Piloté par le contrôle : ni souris ni clavier, et Attendre appelé par lui.
        public bool automatique;
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
        ClientIntention depot;ClientPlan plan;string erreurCellule;
        // Les rues déjà essayées dans la session, posées ou refusées : aucune n'est posée deux fois, ni réessayée.
        readonly HashSet<long> essayees=new();
        RecuIntention enAttente;double prochaineLecture;
        TextMesh panneau,halo;
        const string Aide="Clic : poser un point · Entrée : tracer la route · Échap : annuler";
        const double PeriodeLecture=.25;
        static readonly TimeSpan Delai=TimeSpan.FromSeconds(1);

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
            Cellule=PanneauLieu.LireCellule(Environment.GetCommandLineArgs(),PanneauLieu.CELLULE_PAR_DEFAUT,out erreurCellule);
            Port=PanneauLieu.DEFAULT_SERVICE_PORT;
            if(erreurCellule==null){depot=new ClientIntention(Port,Delai);plan=new ClientPlan(Port,Delai);}
            // Sans matériau, aucune parcelle n'est jamais dessinée : le panneau le dit.
            try{parcelles=new DesertParcelles(transform,roads.terrain);}
            catch(InvalidOperationException e){erreurParcelles=e.Message;}
            // Sans kit, aucun bâtiment n'est jamais dessiné : le panneau le dit.
            try{batiments=new DesertBatiments(transform,roads.terrain);}
            catch(InvalidOperationException e){erreurBatiments=e.Message;}
            Afficher(erreurCellule??erreurParcelles??erreurBatiments??Aide);
        }
        void Start()=>Ouvrir();
        void OnDestroy(){depot?.Dispose();plan?.Dispose();depot=null;plan=null;}
        void Afficher(string texte)
        {
            Message=texte;
            string etat="Terre battue, "+largeur.ToString("0.#")+" m"+(points.Count>0?" · "+points.Count+" point(s)":"");
            panneau.text=texte==Aide?etat+"\n"+Aide:texte+"\n"+etat;halo.text=panneau.text;
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
            if(k.enterKey.wasPressedThisFrame||k.numpadEnterKey.wasPressedThisFrame)Valider();
            if(k.escapeKey.wasPressedThisFrame)Annuler();
        }
        void LateUpdate()=>Placer();

        public bool Clic(Vector2 ecran)
        {
            var ray=view.ScreenPointToRay(ecran);
            if(!roads.terrain.GetComponent<TerrainCollider>().Raycast(ray,out var hit,10000)){Afficher("Ce point n'est pas sur le terrain.");return false;}
            points.Add(roads.PointExact(hit.point));Afficher(Aide);return true;
        }
        public void Annuler(){points.Clear();Recu=null;Afficher(Aide);}

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
            Ouverture.Clear();essayees.Clear();TickOuverture=-1;
            if(erreurCellule!=null){Afficher(erreurCellule);return false;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan à l'ouverture : "+lu.Absence);return false;}
            DesertRoads.Gestes parametres;
            try{parametres=DesertRoads.Lire(roads.implantation);}
            catch(InvalidOperationException e){Afficher(e.Message);return false;}
            roads.Preparer(parametres.parametres,parametres.graine);
            Ouverture.AddRange(Dessiner(lu.Plan));TickOuverture=lu.Plan.Tick;
            // Les parcelles après les rues : leur sol est celui de la copie où les rues sont posées.
            Afficher(Bilan("Plan du tick "+TickOuverture.ToString(CultureInfo.InvariantCulture)+" : "+Ouverture.Count(e=>e.resultat.acceptee)+" rue(s) posée(s).",Ouverture)
                +"\n"+DessinerParcelles(lu.Plan)+"\n"+DessinerBatiments(lu.Plan));
            return true;
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
            return string.Join("\n",new[]{"Bâtiments : "+Batiments.Count(b=>b.etat=="piquets")+" aux piquets, "+Batiments.Count(b=>b.etat=="murs")+" aux murs, "+Batiments.Count(b=>b.etat=="fini")+" fini(s)."}
                .Concat(Batiments.Where(b=>b.etat=="refusee").Select(b=>b.message)));
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
