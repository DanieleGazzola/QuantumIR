module top(x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31, x32, x33, x34, x35, x36, x37, x38, x39, x40, x41, x42, x43, x44, x45, x46, x47, x48, x49, x50, x51, x52, x53, x54, x55, x56, x57, x58, x59, x60, x61, x62, x63, y0);
  input x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31, x32, x33, x34, x35, x36, x37, x38, x39, x40, x41, x42, x43, x44, x45, x46, x47, x48, x49, x50, x51, x52, x53, x54, x55, x56, x57, x58, x59, x60, x61, x62, x63;
  output y0;
  wire n65, n66, n67, n68, n69, n70, n71, n72, n73, n74, n75, n76, n77, n78, n79, n80, n81, n82, n83, n84, n85, n86, n87, n88, n89, n90, n91, n92, n93, n94, n95, n96, n97, n98, n99, n100, n101, n102, n103, n104, n105, n106, n107, n108, n109, n110, n111, n112, n113, n114, n115, n116, n117, n118, n119, n120, n121, n122, n123, n124, n125, n126, n127, n128, n129, n130, n131, n132, n133, n134, n135, n136, n137, n138, n139, n140, n141, n142, n143, n144, n145, n146, n147, n148, n149, n150, n151, n152, n153, n154, n155, n156, n157, n158, n159, n160, n161, n162, n163, n164, n165, n166, n167, n168, n169, n170, n171, n172, n173, n174, n175, n176, n177, n178, n179, n180, n181, n182, n183, n184, n185, n186, n187, n188, n189, n190, n191, n192, n193, n194, n195, n196, n197, n198, n199, n200, n201, n202, n203, n204, n205, n206, n207, n208, n209, n210, n211, n212, n213, n214, n215, n216, n217, n218, n219, n220, n221, n222, n223, n224, n225, n226, n227, n228, n229, n230, n231, n232, n233, n234, n235, n236, n237, n238, n239, n240, n241, n242, n243, n244, n245, n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256, n257, n258, n259, n260, n261, n262, n263, n264, n265, n266, n267;
  assign n65 = x29 & ~x61;
  assign n66 = x28 & ~x60;
  assign n67 = ~n65 & ~n66;
  assign n68 = x30 & ~x62;
  assign n69 = ~x31 & x63;
  assign n70 = ~n68 & ~n69;
  assign n71 = n67 & n70;
  assign n72 = x25 & ~x57;
  assign n73 = x26 & ~x58;
  assign n74 = x27 & ~x59;
  assign n75 = ~n73 & ~n74;
  assign n76 = ~n72 & n75;
  assign n77 = x56 & n76;
  assign n78 = ~x24 & n77;
  assign n79 = x59 ^ x27;
  assign n80 = x58 ^ x26;
  assign n81 = n80 ^ n74;
  assign n82 = x57 ^ x25;
  assign n83 = x57 & ~n82;
  assign n84 = n83 ^ x26;
  assign n85 = n84 ^ x57;
  assign n86 = n81 & ~n85;
  assign n87 = n86 ^ n83;
  assign n88 = n87 ^ x57;
  assign n89 = n88 ^ x59;
  assign n90 = ~n79 & n89;
  assign n91 = n90 ^ x59;
  assign n92 = ~n78 & ~n91;
  assign n93 = n71 & ~n92;
  assign n94 = ~x24 & n76;
  assign n95 = ~n77 & ~n94;
  assign n96 = n71 & ~n95;
  assign n97 = ~x21 & x53;
  assign n98 = ~x20 & x52;
  assign n99 = ~n97 & ~n98;
  assign n100 = x22 & ~x54;
  assign n101 = x21 & ~x53;
  assign n102 = x23 & ~x55;
  assign n103 = ~n101 & ~n102;
  assign n104 = ~n100 & n103;
  assign n105 = ~n99 & n104;
  assign n106 = x55 ^ x23;
  assign n107 = ~x22 & x54;
  assign n108 = n107 ^ x55;
  assign n109 = ~n106 & ~n108;
  assign n110 = n109 ^ x23;
  assign n111 = ~n105 & n110;
  assign n112 = x20 & ~x52;
  assign n113 = n104 & ~n112;
  assign n114 = ~x16 & x48;
  assign n115 = ~x17 & x49;
  assign n116 = ~n114 & ~n115;
  assign n117 = x18 & ~x50;
  assign n118 = x17 & ~x49;
  assign n119 = x19 & ~x51;
  assign n120 = ~n118 & ~n119;
  assign n121 = ~n117 & n120;
  assign n122 = ~n116 & n121;
  assign n123 = x51 ^ x19;
  assign n124 = ~x18 & x50;
  assign n125 = n124 ^ x51;
  assign n126 = ~n123 & ~n125;
  assign n127 = n126 ^ x19;
  assign n128 = ~n122 & n127;
  assign n129 = n113 & ~n128;
  assign n130 = n111 & ~n129;
  assign n131 = n96 & ~n130;
  assign n132 = ~n93 & ~n131;
  assign n133 = x16 & ~x48;
  assign n134 = x47 ^ x15;
  assign n135 = x47 ^ x14;
  assign n136 = n135 ^ x47;
  assign n137 = x47 ^ x46;
  assign n138 = n137 ^ x47;
  assign n139 = ~n136 & n138;
  assign n140 = n139 ^ x47;
  assign n141 = ~n134 & ~n140;
  assign n142 = n141 ^ x15;
  assign n143 = x45 ^ x13;
  assign n144 = x45 ^ x12;
  assign n145 = n144 ^ x45;
  assign n146 = x45 ^ x44;
  assign n147 = n146 ^ x45;
  assign n148 = ~n145 & n147;
  assign n149 = n148 ^ x45;
  assign n150 = ~n143 & ~n149;
  assign n151 = n150 ^ x13;
  assign n155 = x11 & ~x43;
  assign n156 = x10 & ~x42;
  assign n157 = ~n155 & ~n156;
  assign n158 = x9 & ~x41;
  assign n159 = x40 & ~n158;
  assign n160 = n157 & n159;
  assign n161 = ~x8 & ~n158;
  assign n162 = n157 & n161;
  assign n163 = ~n160 & ~n162;
  assign n164 = x5 & ~x37;
  assign n165 = x6 & ~x38;
  assign n166 = x7 & ~x39;
  assign n167 = ~n165 & ~n166;
  assign n168 = ~n164 & n167;
  assign n169 = x36 & n168;
  assign n170 = ~x4 & n168;
  assign n171 = ~n169 & ~n170;
  assign n172 = x35 ^ x3;
  assign n173 = x34 ^ x2;
  assign n175 = x0 & ~x32;
  assign n176 = n175 ^ x34;
  assign n174 = x34 ^ x1;
  assign n177 = n176 ^ n174;
  assign n178 = x34 ^ x33;
  assign n179 = n178 ^ n174;
  assign n180 = n177 & ~n179;
  assign n181 = n180 ^ n174;
  assign n182 = ~n173 & n181;
  assign n183 = n182 ^ x2;
  assign n184 = n183 ^ x35;
  assign n185 = ~n172 & n184;
  assign n186 = n185 ^ x3;
  assign n187 = ~n171 & ~n186;
  assign n188 = ~x4 & n169;
  assign n189 = x39 ^ x7;
  assign n190 = x38 ^ x6;
  assign n191 = n190 ^ n166;
  assign n192 = x37 ^ x5;
  assign n193 = x37 & ~n192;
  assign n194 = n193 ^ x6;
  assign n195 = n194 ^ x37;
  assign n196 = n191 & ~n195;
  assign n197 = n196 ^ n193;
  assign n198 = n197 ^ x37;
  assign n199 = n198 ^ x39;
  assign n200 = ~n189 & n199;
  assign n201 = n200 ^ x39;
  assign n202 = ~n188 & ~n201;
  assign n203 = ~n187 & n202;
  assign n204 = ~n163 & ~n203;
  assign n205 = ~x8 & n160;
  assign n206 = x43 ^ x11;
  assign n207 = x42 ^ x10;
  assign n208 = ~x9 & x41;
  assign n209 = n208 ^ x42;
  assign n210 = ~n207 & n209;
  assign n211 = n210 ^ x42;
  assign n212 = n211 ^ x43;
  assign n213 = ~n206 & n212;
  assign n214 = n213 ^ x43;
  assign n215 = ~n205 & ~n214;
  assign n216 = ~n204 & n215;
  assign n152 = x13 & ~x45;
  assign n153 = x12 & ~x44;
  assign n154 = ~n152 & ~n153;
  assign n217 = n216 ^ n154;
  assign n218 = x14 & ~x46;
  assign n219 = x15 & ~x47;
  assign n220 = ~n218 & ~n219;
  assign n221 = n220 ^ n216;
  assign n222 = ~n216 & ~n221;
  assign n223 = n222 ^ n216;
  assign n224 = ~n217 & ~n223;
  assign n225 = n224 ^ n222;
  assign n226 = n225 ^ n216;
  assign n227 = n226 ^ n220;
  assign n228 = n151 & ~n227;
  assign n229 = n228 ^ n220;
  assign n230 = n142 & ~n229;
  assign n231 = ~n133 & ~n230;
  assign n232 = n121 & n231;
  assign n233 = n113 & n232;
  assign n234 = n96 & n233;
  assign n235 = x63 ^ x31;
  assign n236 = x61 ^ x29;
  assign n237 = x61 ^ x28;
  assign n238 = n237 ^ x61;
  assign n239 = x61 ^ x60;
  assign n240 = n239 ^ x61;
  assign n241 = ~n238 & n240;
  assign n242 = n241 ^ x61;
  assign n243 = ~n236 & ~n242;
  assign n244 = n243 ^ x29;
  assign n245 = n244 ^ x63;
  assign n246 = n245 ^ x63;
  assign n247 = n68 ^ x63;
  assign n248 = n247 ^ x63;
  assign n249 = ~n246 & ~n248;
  assign n250 = n249 ^ x63;
  assign n252 = n250 ^ x62;
  assign n253 = n252 ^ n250;
  assign n251 = n250 ^ x63;
  assign n254 = n253 ^ n251;
  assign n255 = n250 ^ x30;
  assign n256 = n255 ^ n250;
  assign n257 = n256 ^ n253;
  assign n258 = n253 & ~n257;
  assign n259 = n258 ^ n253;
  assign n260 = ~n254 & n259;
  assign n261 = n260 ^ n258;
  assign n262 = n261 ^ n250;
  assign n263 = n262 ^ n253;
  assign n264 = ~n235 & n263;
  assign n265 = n264 ^ x31;
  assign n266 = ~n234 & ~n265;
  assign n267 = n132 & n266;
  assign y0 = ~n267;
endmodule