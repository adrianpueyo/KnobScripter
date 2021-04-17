blink_keywords = ["eComponentWise","ePixelWise","ImageComputationKernel","ImageRollingKernel","ImageReductionKernel",
                  "eRead","eWrite","eReadWrite","kernel",
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

blink_keyword_dict = {
                "Access Pattern": {
                    "keywords": ["eAccessPoint", "eAccessRanged1D", "eAccessRanged2D", "eAccessRandom"],
                    "help": '''This describes how the kernel will access pixels in the image. The options are:
                                <ul>
                                    <li><b>eAccessPoint</b>: Access only the current position in the iteration space.</li>
                                    <li><b>eAccessRanged1D</b>: Access a one-dimensional range of positions relative to the current position in the iteration space.</li>
                                    <li><b>eAccessRanged2D</b>: Access a two-dimensional range of positions relative to the current position in the iteration space.</li>
                                    <li><b>eAccessRandom</b>: Access any pixel in the iteration space.</li>
                                </ul>
                                The default value is <b>eAccessPoint</b>.
                            '''
                },
                "Edge Method": {
                    "keywords": ["eEdgeClamped", "eEdgeConstant", "eEdgeNone"],
                    "help": '''The edge method for an image defines the behaviour if a kernel function tries to access data outside the image bounds. The options are:
                                <ul>
                                    <li><b>eEdgeClamped</b>: The edge values will be repeated outside the image bounds.</li>
                                    <li><b>eEdgeConstant</b>: Zero values will be returned outside the image bounds.</li>
                                    <li><b>eEdgeNone</b>: Values are undefined outside the image bounds and no within-bounds checks will be done when you access the image. This is the most efficient access method to use when you do not require access outside the bounds, because of the lack of bounds checks.</li>
                                </ul>
                                The default value is <b>eEdgeNone</b>.
                            '''
                },
                "Kernel Granularity": {
                    "keywords": ["eComponentWise", "ePixelWise"],
                    "help": '''A kernel can be iterated in either a componentwise or pixelwise manner. Componentwise iteration means that the kernel will be executed once for each component at every point in the iteration space. Pixelwise means it will be called once only for every point in the iteration space. The options for the kernel granularity are:
                                <ul>
                                    <li><b>eComponentWise</b>: The kernel processes the image one component at a time. Only the current component's value can be accessed in any of the input images, or written to in the output image.</li>
                                    <li><b>ePixelWise</b>: The kernel processes the image one pixel at a time. All component values can be read from and written to.</li>
                                </ul>
                            '''
                },
                "Read Spec": {
                    "keywords": ["eRead", "eWrite", "eReadWrite"],
                    "help": '''This describes how the data in the image can be accessed. The options are:
                                <ul>
                                    <li><b>eRead</b>: Read-only access to the image data. <i>Common for the input image/s.</i></li>
                                    <li><b>eWrite</b>: Write-only access to the image data. <i>Common for the output image.</i></li>
                                    <li><b>eReadWrite</b>: Both read and write access to the image data. <i>Useful when you need to write and read again from the output image.</i></li>
                                </ul>
                            '''
                },
                "Variable Types": {
                    "keywords": ["int", "int2", "int3", "int4", "float", "float2", "float3", "float4", "float3x3",
                                 "float4x4", "bool"],
                    "help": '''<p>Both param and local variables can be standard C++ types such as float, int and bool.</p>
                               <p>Arrays of C++ types are also supported: float[], int[], bool[].</p>
                               <p>In addition, there are some standard vector types: int2, int3, int4, float2, float3 and float4. For completeness, we also provide the vector types int1 and float1.</p>
                               <p>Individual components of vector types can be accessed using .x, .y, .z and .w for the first, second, third and fourth components respectively. For example, if you have a variable of a vector type called vec, the first component can be accessed using vec.x.</p>
                            '''
                },
                "Kernel Type": {
                    "keywords": ["ImageComputationKernel", "ImageRollingKernel", "ImageReductionKernel"],
                    "help": '''<p>Please note <b>only ImageComputationKernel is compatible with the BlinkScript node</b>. Only use the other types if you're writing Blink for a compiled plugin.</p>
                                <p>There are three types of Blink kernel:</p>
                                <ul>
                                    <li><b>ImageComputationKernel</b>: used for image processing, this takes zero or more images as input and produces one or more images as output.</li>
                                    <li><b>ImageRollingKernel</b>: also used for image processing, where there is a data dependency between the output at different points in the output space. With an ImageComputationKernel, there are no guarantees about the order in which the output pixels will be filled in. With an ImageRollingKernel, you can choose to "roll" the kernel either horizontally or vertically over the iteration bounds, allowing you to carry data along rows or down columns respectively.</li>
                                    <li><b>ImageReductionKernel</b>: used to "reduce" an image down to a value or set of values that represent it, for example to calculate statistics such as the mean or variance of an image.</li>
                                </ul>
                            '''
                },
            }

default_snippets = {
                        "all": [
                            ["b","[$$]"], # In the nuke panes, most times Nuke doesn't allow the [] keys with is a pain
                        ],
                        "blink": [
                            ["img","Image<eRead, eAccessPoint, eEdgeClamped> $$src$$;"],
                            ["kernel","kernel $$SaturationKernel$$ : ImageComputationKernel <ePixelWise>\n{\n\n}"],
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
                            ["deselect","[n.setSelected(False) for n in $$nuke.selectedNodes()$$]"],
                        ]
                    }

# Initialized at runtime
all_snippets = []