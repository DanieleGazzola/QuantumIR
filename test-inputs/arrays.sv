module vectorOperations(
    input  logic [5:0] v1, v2,
    input  logic a, b,
    output logic [5:0] out1, out2, out3
);

   // Assegnazione di valori ai vettori       
   assign out1 = v1 ^ v2; 
   assign out2 = ~ v1;

   // Operazione AND elemento per elemento tra i vettori
   assign out3 = a & b;

endmodule