blink_keywords = ["eComponentWise","ePixelWise","ImageComputationKernel",
                  "Image <eRead, eAccessPoint, eEdgeClamped> $$src$$;",
                  "eRead","eWrite","eReadWrite","kernel ",
                  "eAccessPoint","eAccessRanged1D","eAccessRanged2D","eAccessRandom",
                  "setAxis($$eX$$)","setRange($$)","defineParam($$paramName, \"label\", defaultValue$$)",
                  "kMin","kMax","kWhitePoint","kComps","kClamps","bounds",
                  "ValueType($$image$$)","SampleType($$image$$)",
                  "float ","float2 ","float3 ","float4 ","float3x3 ","float4x4 ","float[] ",
                  "int ","int2 ","int3 ","int4 ","int3x3 ",
                  "process($$int2 pos$$)","init()","param:","local:",
                  "bilinear($$)","dot($$vec a, vec b$$)","cross","length","normalize",
                  "sin($$)","cos($$)","tan($$)","asin($$)","acos($$)","atan($$)","atan2($$)",
                  "exp($$)","log($$)","log2($$)","log10($$)",
                  "floor($$)","ceil($$)","round($$)","pow($$a, b$$)","sqrt($$)","rsqrt($$)",
                  "fabs($$)","abs($$)","fmod($$)","modf($$)","sign($$)",
                  "min($$)","max($$)","clamp($$type a, type min($$), type max($$)","rcp($$)",
                  "atomicAdd($$)","atomicInc($$)","median($$)",
                  "rect($$scalar x1, scalar y1, scalar x2, scalar y2$$)","grow($$scalar x, scalar y$$)",
                  "inside($$vec v$$)","width()","height()",
                  ]

default_snippets = {
                        "all": [
                            ["b","[$$]"]
                        ],
                        "blink": [
                            ["img","Image<eRead, eAccessPoint, eEdgeClamped> $$src$$;"],
                            ["kernel","kernel $$SaturationKernel$$ : ImageComputationKernel <ePixelWise>"],
                            ["Image","Image<eRead, eAccessPoint, eEdgeClamped> $$src$$;"]
                        ],
                        "python": [
                            ["try","try:\n    $$\nexcept:\n    pass"],
                            ["tn","nuke.thisNode()"],
                            ["tk","nuke.thisKnob()"],
                            ["sns","nuke.selectedNodes()"],
                            ["sn","nuke.selectedNode()"],
                            ["ntn","nuke.toNode($$)"],
                            ["p","print($$)"],
                            ["an","nuke.allNodes($$)"],
                            ["deselect","[n.setSelected(False) for n in $$nuke.selectedNodes()$$]"]
                        ]
                    }

# Initialized at runtime
all_snippets = []