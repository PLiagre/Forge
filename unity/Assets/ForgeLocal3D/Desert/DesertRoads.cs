using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Splines;

namespace ForgeLocal3D
{
    // Routes du joueur (lot 263). Un geste — des points, une largeur, un revêtement — devient une
    // spline échantillonnée au pas du terrain. Le profil en long est la moyenne glissante du
    // terrain sous l'axe ; au-delà de la pente maximale, ou si le talus 1:2 ne rejoint pas le
    // terrain à la distance fixée, la route est refusée et rien ne change. Sinon le terrain
    // s'aplanit sous la largeur, le talus rejoint le sol d'origine, la chaussée se peint et
    // perd ses touffes.
    //
    // Tout se fait sur une copie du TerrainData : l'asset reste intact. Les paramètres viennent
    // de local3d/desert/routes.py, qui écrit gestes.json ; le même module rejoue chaque route et
    // juge ce qu'Unity a obtenu. Les calculs de distance suivent routes.plus_proche pas à pas,
    // dans le même ordre, pour que les deux côtés choisissent le même point de l'axe.
    [RequireComponent(typeof(SplineContainer))]
    public sealed class DesertRoads : MonoBehaviour
    {
        [Serializable] public class Parametres { public double pas=-1,fenetre=-1,pente_max=-1,talus=-1,talus_max=-1,bruit_bord=-1,fondu_bord=-1,arrondi=-1; }
        [Serializable] public class Geste { public string id,famille,revetement;public double largeur;public double[] x,y; }
        [Serializable] public class Gestes { public string implantation;public int graine;public Parametres parametres;public Geste[] routes; }
        public sealed class Resultat
        {
            public bool acceptee;public string motif="",message="";public double valeur=-1,position=-1,longueur=-1;
            public double[] ax=new double[0],ay=new double[0],profil=new double[0];
        }
        public sealed class Empreinte { public string hauteurs="",couches="",touffes=""; public string Tout=>hauteurs+couches+touffes; }

        public const string Sorties="../local3d/desert/sorties/ville/";
        public Terrain terrain;public TerrainLayer terreBattue,paves;public string implantation;public int graine;

        TerrainData original;
        public TerrainData Copie{get;private set;}
        public Parametres Actuels{get;private set;}
        int seed,n,m,dn,couches;double @base,hauteur,taille,pas;
        float[,] heights;

        public static string CheminGestes(string id)=>Sorties+id+"/routes/gestes.json";

        // Sans gestes.json, les paramètres manquent : on refuse de les deviner.
        public static Gestes Lire(string id)
        {
            string path=CheminGestes(id);
            if(!File.Exists(path))throw new InvalidOperationException("Paramètres des routes absents ("+path+") : lancer py local3d/atelier_desert.py routes");
            var g=JsonUtility.FromJson<Gestes>(File.ReadAllText(path));
            var p=g?.parametres;
            if(p==null||p.pas<=0||p.fenetre<=0||p.pente_max<=0||p.talus<=0||p.talus_max<=0||p.bruit_bord<0||p.fondu_bord<=0||p.arrondi<=0)
                throw new InvalidOperationException("Paramètres des routes incomplets : "+path);
            return g;
        }

        // ---------- La copie du terrain ----------

        public void Preparer(Parametres p,int graineDuBord)
        {
            if(!original)original=terrain.terrainData;
            if(Copie)Destroy(Copie);
            Actuels=p;seed=graineDuBord;
            var o=original;n=o.heightmapResolution;taille=o.size.x;hauteur=o.size.y;@base=terrain.transform.position.y;pas=taille/(n-1);
            heights=o.GetHeights(0,0,n,n);
            var c=new TerrainData{name=o.name+" — routes"};
            c.heightmapResolution=n;c.size=o.size;c.SetHeights(0,0,heights);
            m=o.alphamapResolution;var a0=o.GetAlphamaps(0,0,m,m);int k0=a0.GetLength(2);
            c.alphamapResolution=m;c.baseMapResolution=o.baseMapResolution;
            c.terrainLayers=o.terrainLayers.Concat(new[]{terreBattue,paves}).ToArray();couches=k0+2;
            var a=new float[m,m,couches];
            for(int j=0;j<m;j++)for(int i=0;i<m;i++)for(int k=0;k<k0;k++)a[j,i,k]=a0[j,i,k];
            c.SetAlphamaps(0,0,a);
            dn=o.detailResolution;c.SetDetailResolution(dn,o.detailResolutionPerPatch);c.SetDetailScatterMode(o.detailScatterMode);
            c.detailPrototypes=o.detailPrototypes;
            c.wavingGrassAmount=o.wavingGrassAmount;c.wavingGrassSpeed=o.wavingGrassSpeed;c.wavingGrassStrength=o.wavingGrassStrength;c.wavingGrassTint=o.wavingGrassTint;
            for(int l=0;l<o.detailPrototypes.Length;l++)c.SetDetailLayer(0,0,l,o.GetDetailLayer(0,0,dn,dn,l));
            terrain.terrainData=c;terrain.GetComponent<TerrainCollider>().terrainData=c;Copie=c;
            var box=GetComponent<SplineContainer>();foreach(var s in box.Splines.ToArray())box.RemoveSpline(s);
        }
        void Assure(){if(!Copie){var g=Lire(implantation);Preparer(g.parametres,g.graine);}}
        public void Restaurer()
        {
            if(!original)return;
            terrain.terrainData=original;terrain.GetComponent<TerrainCollider>().terrainData=original;
            if(Copie)Destroy(Copie);Copie=null;
        }
        void OnDestroy()=>Restaurer();

        public static Empreinte Empreintes(TerrainData td)
        {
            using var sha=SHA256.Create();
            string Hex(byte[] b)=>BitConverter.ToString(sha.ComputeHash(b)).Replace("-","").ToLowerInvariant();
            string H(Array a,int bytes){var b=new byte[bytes];Buffer.BlockCopy(a,0,b,0,bytes);return Hex(b);}
            int hn=td.heightmapResolution,am=td.alphamapResolution,dr=td.detailResolution;
            var h=td.GetHeights(0,0,hn,hn);var a=td.GetAlphamaps(0,0,am,am);
            var d=new List<byte>();
            for(int l=0;l<td.detailPrototypes.Length;l++){var g=td.GetDetailLayer(0,0,dr,dr,l);var b=new byte[g.Length*4];Buffer.BlockCopy(g,0,b,0,b.Length);d.AddRange(b);}
            return new Empreinte{hauteurs=H(h,h.Length*4),couches=H(a,a.Length*4),touffes=Hex(d.ToArray())};
        }
        public Empreinte Empreintes()=>Empreintes(Copie?Copie:terrain.terrainData);

        // ---------- Le geste ----------

        public double Arrondi(double v){double k=Math.Round(1/Actuels.arrondi);return Math.Round(v*k)/k;}
        // Point du joueur dans le repère de paysage.py, arrondi au centimètre.
        public (double x,double y) PointExact(Vector3 monde){Assure();return (Arrondi(-monde.x),Arrondi(-monde.z));}

        // La spline passe par les points ; elle est rééchantillonnée à pas égaux, au plus près du pas du terrain.
        public Spline Axe(double[] x,double[] y,out double[] ax,out double[] ay)
        {
            var knots=new List<float3>();for(int i=0;i<x.Length;i++)knots.Add(new float3(-(float)x[i],0,-(float)y[i]));
            var spline=SplineFactory.CreateCatmullRom(knots);
            float length=spline.GetLength();int dense=Math.Max(2,Mathf.CeilToInt(length/.02f));
            var px=new double[dense+1];var py=new double[dense+1];var c=new double[dense+1];
            for(int i=0;i<=dense;i++)
            {
                float3 q=spline.EvaluatePosition((float)i/dense);px[i]=-(double)q.x;py[i]=-(double)q.z;
                if(i>0){double dx=px[i]-px[i-1],dy=py[i]-py[i-1];c[i]=c[i-1]+Math.Sqrt(dx*dx+dy*dy);}
            }
            int count=Math.Max(1,(int)Math.Round(c[dense]/Actuels.pas));ax=new double[count+1];ay=new double[count+1];int seg=0;
            for(int k=0;k<=count;k++)
            {
                double target=c[dense]*k/count;
                while(seg<dense-1&&c[seg+1]<target)seg++;
                double span=c[seg+1]-c[seg],t=span>0?(target-c[seg])/span:0;
                ax[k]=Math.Round((px[seg]+t*(px[seg+1]-px[seg]))*1e4)/1e4;ay[k]=Math.Round((py[seg]+t*(py[seg+1]-py[seg]))*1e4)/1e4;
            }
            return spline;
        }

        double Metres(int j,int i)=>heights[j,i]*hauteur+@base;
        // Comme la surface d'un Unity Terrain : chaque carreau coupé le long de la diagonale (i, j)–(i+1, j+1).
        double Hauteur(double x,double y)
        {
            double u=(taille/2-x)/pas,v=(taille/2-y)/pas;
            int i=Math.Clamp((int)Math.Floor(u),0,n-2),j=Math.Clamp((int)Math.Floor(v),0,n-2);double fu=u-i,fv=v-j;
            double a=Metres(j,i),b=Metres(j,i+1),c=Metres(j+1,i),e=Metres(j+1,i+1);
            return fu>fv?a+(b-a)*fu+(e-b)*fv:a+(c-a)*fv+(e-c)*fu;
        }
        static double[] Longueurs(double[] ax,double[] ay)
        {
            var s=new double[ax.Length];
            for(int k=1;k<ax.Length;k++){double dx=ax[k]-ax[k-1],dy=ay[k]-ay[k-1];s[k]=s[k-1]+Math.Sqrt(dx*dx+dy*dy);}
            return s;
        }
        // Moyenne glissante centrée, en échantillons ; elle rétrécit des deux côtés aux bouts.
        public double[] Profil(double[] ax,double[] ay)
        {
            int count=ax.Length,half=Math.Max(1,(int)Math.Round(Actuels.fenetre/(2*Actuels.pas)));
            var h0=new double[count];for(int k=0;k<count;k++)h0[k]=Hauteur(ax[k],ay[k]);
            var c=new double[count+1];for(int k=0;k<count;k++)c[k+1]=c[k]+h0[k];
            var p=new double[count];
            for(int k=0;k<count;k++){int w=Math.Min(half,Math.Min(k,count-1-k));p[k]=(c[k+w+1]-c[k-w])/(2*w+1);}
            return p;
        }

        // Pour chaque point d'une grille (sommets ou cellules) proche de l'axe : distance, et valeurs au projeté.
        sealed class Fenetre{public int i0,j0,w,h;public double[] D;public double[][] V;}
        Fenetre PlusProche(double[] ax,double[] ay,double[][] valeurs,double rayon,int count,double step,double off)
        {
            double half=taille/2;
            var f=new Fenetre();
            f.i0=Math.Max(0,(int)Math.Floor((half-(ax.Max()+rayon))/step-off)-1);int i1=Math.Min(count-1,(int)Math.Ceiling((half-(ax.Min()-rayon))/step-off)+1);
            f.j0=Math.Max(0,(int)Math.Floor((half-(ay.Max()+rayon))/step-off)-1);int j1=Math.Min(count-1,(int)Math.Ceiling((half-(ay.Min()-rayon))/step-off)+1);
            f.w=i1-f.i0+1;f.h=j1-f.j0+1;f.D=Enumerable.Repeat(double.PositiveInfinity,f.w*f.h).ToArray();
            f.V=valeurs.Select(_=>new double[f.w*f.h]).ToArray();
            for(int k=0;k+1<ax.Length;k++)
            {
                double x0=ax[k],y0=ay[k],sx=ax[k+1]-x0,sy=ay[k+1]-y0,l2=sx*sx+sy*sy;
                int a=Math.Max(0,(int)Math.Floor((half-(Math.Max(x0,ax[k+1])+rayon))/step-off)-1-f.i0),b=Math.Min(f.w-1,(int)Math.Ceiling((half-(Math.Min(x0,ax[k+1])-rayon))/step-off)+1-f.i0);
                int c=Math.Max(0,(int)Math.Floor((half-(Math.Max(y0,ay[k+1])+rayon))/step-off)-1-f.j0),e=Math.Min(f.h-1,(int)Math.Ceiling((half-(Math.Min(y0,ay[k+1])-rayon))/step-off)+1-f.j0);
                for(int jj=c;jj<=e;jj++)
                {
                    double dy=half-(f.j0+jj+off)*step-y0;
                    for(int ii=a;ii<=b;ii++)
                    {
                        double dx=half-(f.i0+ii+off)*step-x0;
                        double t=l2>0?Math.Clamp((dx*sx+dy*sy)/l2,0,1):0;
                        double ex=dx-t*sx,ey=dy-t*sy,d=Math.Sqrt(ex*ex+ey*ey);int idx=jj*f.w+ii;
                        if(d<f.D[idx]){f.D[idx]=d;for(int v=0;v<valeurs.Length;v++)f.V[v][idx]=valeurs[v][k]+t*(valeurs[v][k+1]-valeurs[v][k]);}
                    }
                }
            }
            return f;
        }

        // Bruit de valeur : le bord peint ondule, de la même façon à graine égale.
        static double Hache(double a,double b,int s){double q=Math.Sin(a*127.1+b*311.7+s*91.17)*43758.5453;return q-Math.Floor(q);}
        static double Bruit(double x,double y,int s)
        {
            double ix=Math.Floor(x),iy=Math.Floor(y),fx=x-ix,fy=y-iy;fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy);
            return (Hache(ix,iy,s)*(1-fx)+Hache(ix+1,iy,s)*fx)*(1-fy)+(Hache(ix,iy+1,s)*(1-fx)+Hache(ix+1,iy+1,s)*fx)*fy;
        }

        static Resultat Refus(Resultat r,string motif,double valeur,double position,string message)
        {r.acceptee=false;r.motif=motif;r.valeur=valeur;r.position=position;r.message=message;return r;}

        // Pose une route, ou la refuse sans rien changer. `decalage` relève le profil (contre-épreuve) ;
        // `penteMax` remplace la pente maximale des paramètres (contre-épreuve).
        public Resultat Poser(Geste g,double decalage=0,double penteMax=double.NaN)
        {
            Assure();var P=Actuels;var r=new Resultat();
            double pmax=double.IsNaN(penteMax)?P.pente_max:penteMax;
            if(g.x==null||g.y==null||g.x.Length<2||g.x.Length!=g.y.Length)return Refus(r,"points",-1,-1,"Il faut au moins deux points.");
            var x=g.x.Select(Arrondi).ToArray();var y=g.y.Select(Arrondi).ToArray();
            for(int i=1;i<x.Length;i++)if(x[i]==x[i-1]&&y[i]==y[i-1])return Refus(r,"points",-1,-1,"Deux points confondus.");
            int layer=g.revetement=="paves"?couches-1:g.revetement=="terre"?couches-2:-1;
            if(layer<0)return Refus(r,"revetement",-1,-1,"Revêtement inconnu : "+g.revetement);
            if(!(g.largeur>0))return Refus(r,"largeur",-1,-1,"Largeur nulle.");
            var spline=Axe(x,y,out var ax,out var ay);r.ax=ax;r.ay=ay;
            double demi=g.largeur/2,R=demi+P.talus_max,bord=demi+P.bruit_bord+P.fondu_bord/2;
            if(ax.Concat(ay).Any(v=>Math.Abs(v)>taille/2-R-pas))return Refus(r,"hors_terrain",-1,-1,"La route sort du terrain.");
            var s=Longueurs(ax,ay);r.longueur=s[^1];
            var p=Profil(ax,ay);for(int k=0;k<p.Length;k++)p[k]+=decalage;r.profil=p;

            // 1. Le profil en long.
            double g1=0,ou=0;
            for(int k=0;k+1<p.Length;k++){double v=Math.Abs(p[k+1]-p[k])/Math.Max(s[k+1]-s[k],1e-9);if(v>g1){g1=v;ou=(s[k]+s[k+1])/2;}}
            r.valeur=g1;r.position=ou;
            if(g1>pmax)return Refus(r,"pente",g1,ou,$"Route refusée : pente de {g1*100:0} % à {ou:0} m du départ ({pmax*100:0} % au plus).");

            // 2. Le terrain : chaussée au profil, talus attaché à la chaussée, rien au-delà.
            var f=PlusProche(ax,ay,new[]{p,s},R,n,pas,0);
            int W=f.w,H=f.h,N=W*H;var h0=new double[N];var lim=new double[N];var exces=new double[N];
            var chaussee=new bool[N];var rabot=new bool[N];
            for(int jj=0;jj<H;jj++)for(int ii=0;ii<W;ii++)
            {
                int q=jj*W+ii;double d=f.D[q];h0[q]=Metres(f.j0+jj,f.i0+ii);lim[q]=(d-demi)*P.talus;exces[q]=Math.Abs(h0[q]-f.V[0][q])-lim[q];
                chaussee[q]=d<=demi;rabot[q]=d>demi&&d<=R&&exces[q]>0;
            }
            // Le talus : les sommets rabotés reliés à la chaussée de proche en proche (quatre voisins).
            var talus=new bool[N];var file=new Queue<int>();
            void Voisins(int q,Action<int> faire){int ii=q%W,jj=q/W;if(ii>0)faire(q-1);if(ii<W-1)faire(q+1);if(jj>0)faire(q-W);if(jj<H-1)faire(q+W);}
            for(int q=0;q<N;q++)if(rabot[q]){bool pres=false;Voisins(q,v=>pres|=chaussee[v]);if(pres){talus[q]=true;file.Enqueue(q);}}
            while(file.Count>0){int q=file.Dequeue();Voisins(q,v=>{if(rabot[v]&&!talus[v]){talus[v]=true;file.Enqueue(v);}});}
            double pire=-1,lieu=-1;
            for(int q=0;q<N;q++)if(talus[q]&&f.D[q]>R-pas&&exces[q]>pire){pire=exces[q];lieu=f.V[1][q];}
            if(pire>0)return Refus(r,"talus",pire,lieu,$"Route refusée : à {lieu:0} m du départ, le talus ne rejoint pas le terrain à {P.talus_max:0} m du bord.");
            var region=new float[H,W];
            for(int jj=0;jj<H;jj++)for(int ii=0;ii<W;ii++)
            {
                int q=jj*W+ii;double v=h0[q];double pp=f.V[0][q];
                if(chaussee[q])v=pp;else if(talus[q])v=Math.Min(Math.Max(h0[q],pp-lim[q]),pp+lim[q]);
                double norm=(v-@base)/hauteur;
                if(norm<0||norm>1)return Refus(r,"boite",v,f.V[1][q],"Route refusée : le terrain sortirait de sa boîte de hauteurs.");
                region[jj,ii]=chaussee[q]||talus[q]?(float)norm:heights[f.j0+jj,f.i0+ii];
            }
            for(int jj=0;jj<H;jj++)for(int ii=0;ii<W;ii++)heights[f.j0+jj,f.i0+ii]=region[jj,ii];
            Copie.SetHeights(f.i0,f.j0,region);

            // 3. Le sol : le revêtement, bord irrégulier ; les autres couches s'effacent d'autant.
            var fa=PlusProche(ax,ay,new double[0][],bord,m,taille/m,.5);
            var alpha=Copie.GetAlphamaps(fa.i0,fa.j0,fa.w,fa.h);
            for(int jj=0;jj<fa.h;jj++)for(int ii=0;ii<fa.w;ii++)
            {
                double d=fa.D[jj*fa.w+ii];if(!(d<=bord))continue;
                double px=taille/2-(fa.i0+ii+.5)*(taille/m),py=taille/2-(fa.j0+jj+.5)*(taille/m);
                double onde=.75*(2*Bruit(px*.4,py*.4,seed+263)-1)+.25*(2*Bruit(px*1.3,py*1.3,seed+264)-1);
                double e=demi+P.bruit_bord*onde,w=Math.Clamp((e-d)/P.fondu_bord+.5,0,1);
                if(w<=0)continue;
                for(int k=0;k<couches;k++)alpha[jj,ii,k]*=(float)(1-w);
                alpha[jj,ii,layer]+=(float)w;
            }
            Copie.SetAlphamaps(fa.i0,fa.j0,alpha);

            // 4. Aucune touffe sur la chaussée peinte.
            if(Copie.detailPrototypes.Length>0)
            {
                var fd=PlusProche(ax,ay,new double[0][],bord,dn,taille/dn,.5);
                for(int l=0;l<Copie.detailPrototypes.Length;l++)
                {
                    var cells=Copie.GetDetailLayer(fd.i0,fd.j0,fd.w,fd.h,l);
                    for(int jj=0;jj<fd.h;jj++)for(int ii=0;ii<fd.w;ii++)if(fd.D[jj*fd.w+ii]<=bord)cells[jj,ii]=0;
                    Copie.SetDetailLayer(fd.i0,fd.j0,l,cells);
                }
            }
            GetComponent<SplineContainer>().AddSpline(spline);
            r.acceptee=true;r.message=$"Route posée : {s[^1]:0} m, pente maximale {g1*100:0} %.";
            return r;
        }
    }
}
