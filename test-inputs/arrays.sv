module vectorOperations(
    input logic [5:0] vector1, vector2,
    input logic a,b,
    output logic [5:0] prova1,prova2,prova3
);

    // Assegnazione di valori ai vettori e allo scalare        
   // Operazione AND elemento per elemento tra i vettori
   assign prova1 = vector1 ^ vector2; 
   assign prova2 = ~ vector1;
   assign prova3 = a & b;

endmodule