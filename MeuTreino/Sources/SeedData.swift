import Foundation
import SwiftData

// Preenche um exemplo na primeira vez que o app abre, só para você ver funcionando.
// Depois é só apagar e pôr os seus dados.
enum SeedData {
    static func popularSeVazio(_ context: ModelContext) {
        let qtd = (try? context.fetchCount(FetchDescriptor<Treino>())) ?? 0
        guard qtd == 0 else { return }

        let treino = Treino(nome: "Treino A — Peito e Tríceps")
        context.insert(treino)

        let supino = Exercicio(nome: "Supino reto", grupo: "Peito", ordem: 1,
                               observacao: "Senti o ombro na última série.")
        supino.treino = treino
        treino.exercicios.append(supino)
        context.insert(supino)

        for i in 1...3 {
            let s = Serie(ordem: i, cargaKg: 20, repeticoes: 12, feedback: "médio")
            s.exercicio = supino
            supino.series.append(s)
            context.insert(s)
        }

        context.insert(Nota(texto: "Primeira nota: comecei a usar o Meu Treino hoje."))
    }
}
