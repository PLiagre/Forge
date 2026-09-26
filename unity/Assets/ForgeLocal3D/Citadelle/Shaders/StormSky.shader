Shader "Forge/StormSky"
{
    Properties { _Night("Nuit",Range(0,1))=0 }
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
            float _Night;
            struct V {float4 position:SV_POSITION;float3 direction:TEXCOORD0;};
            V vert(float4 vertex:POSITION){V o;o.position=UnityObjectToClipPos(vertex);o.direction=vertex.xyz;return o;}
            float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
            float4 frag(V i):SV_Target
            {
                float3 d=normalize(i.direction);float2 p=d.xz/max(.16,d.y+.32)*1.2+float2(_Time.y*.006,0);
                float n=0,a=.55;for(int j=0;j<5;j++){n+=a*noise(p);p=p*2.13+3.7;a*=.5;}
                float c=smoothstep(.25,.78,n);
                float3 col=lerp(float3(.035,.06,.09),float3(.35,.43,.48),c);
                col=lerp(col,float3(.22,.29,.35),pow(saturate(1-d.y),9)*.45);
                return float4(col*lerp(1,.31,_Night),1);
            }
            ENDHLSL
        }
    }
}
