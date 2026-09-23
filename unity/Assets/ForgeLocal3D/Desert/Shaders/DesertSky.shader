Shader "Forge/DesertSky"
{
    // Ciel du désert : bleu profond au zénith, voile de poussière à l'horizon,
    // halo du soleil, cirrus étirés. Crépuscule, nuit et tempête se règlent par propriétés.
    Properties
    {
        _Night("Nuit",Range(0,1))=0
        _Dusk("Crépuscule",Range(0,1))=0
        _Dust("Poussière",Range(0,1))=0
        _SunDirection("Direction du soleil",Vector)=(0,.4,1,0)
    }
    SubShader
    {
        Tags {"Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox"}
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            float _Night,_Dusk,_Dust;float4 _SunDirection;
            struct V {float4 position:SV_POSITION;float3 direction:TEXCOORD0;};
            V vert(float4 vertex:POSITION){V o;o.position=UnityObjectToClipPos(vertex);o.direction=vertex.xyz;return o;}
            float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
            float4 frag(V i):SV_Target
            {
                float3 d=normalize(i.direction);float up=saturate(d.y);
                float3 zenith=lerp(float3(.10,.26,.56),float3(.20,.24,.42),_Dusk);
                float3 horizon=lerp(float3(.80,.66,.50),float3(.96,.52,.26),_Dusk);
                float3 col=lerp(horizon,zenith,pow(up,.45));
                col=lerp(col,float3(.55,.60,.68),exp(-up*9)*.25*(1-_Dusk));
                // Cirrus étirés dans le sens du vent, plus visibles loin de l'horizon.
                float2 p=d.xz/max(.12,d.y+.2)*float2(.6,2.4)+float2(_Time.y*.004,0);
                float n=0,a=.55;for(int j=0;j<4;j++){n+=a*noise(p);p=p*2.07+1.3;a*=.5;}
                float cloud=smoothstep(.55,.85,n)*smoothstep(.02,.25,up)*.45;
                col=lerp(col,lerp(float3(1,.96,.9),float3(1,.62,.40),_Dusk),cloud);
                float3 s=normalize(_SunDirection.xyz);float c=saturate(dot(d,s));
                col+=lerp(float3(1,.82,.6),float3(1,.5,.22),_Dusk)*(pow(c,600)*18+pow(c,12)*.35+pow(c,3)*.08*_Dusk);
                col=lerp(col,float3(.78,.60,.42),_Dust*(1-up*.5));
                float3 night=lerp(float3(.05,.06,.10),float3(.012,.018,.04),up);
                float star=step(.9965,hash(floor(d.xz/max(.05,d.y+.05)*260)))*up;
                night+=star*.6;
                return float4(lerp(col,night,_Night),1);
            }
            ENDHLSL
        }
    }
}
