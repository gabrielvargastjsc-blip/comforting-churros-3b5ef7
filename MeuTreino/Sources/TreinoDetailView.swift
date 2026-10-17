import SwiftUI
import SwiftData

// Detalhe de um treino: nome, data, e a lista de exercícios.
struct TreinoDetailView: View {
    @Bindable var treino: Treino
    @Environment(\.modelContext) private var context

    private var exerciciosOrdenados: [Exercicio] {
        treino.exercicios.sorted { $0.ordem < $1.ordem }
    }

    var body: some View {
        Form {
            Section("Treino") {
                TextField("Nome", text: $treino.nome)
                DatePicker("Data", selection: $treino.data, displayedComponents: .date)
                Toggle("Concluído", isOn: $treino.concluido)
            }
            Section("Exercícios") {
                ForEach(exerciciosOrdenados) { ex in
                    NavigationLink {
                        ExercicioView(exercicio: ex)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(ex.nome.isEmpty ? "Exercício" : ex.nome)
                            Text("\(ex.series.count) série(s)")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete(perform: apagarExercicio)
                Button(action: adicionarExercicio) {
                    Label("Adicionar exercício", systemImage: "plus")
                }
            }
        }
        .navigationTitle("Treino")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func adicionarExercicio() {
        let ex = Exercicio(nome: "Novo exercício",
                           ordem: (exerciciosOrdenados.last?.ordem ?? 0) + 1)
        ex.treino = treino
        treino.exercicios.append(ex)
        context.insert(ex)
    }

    private func apagarExercicio(_ offsets: IndexSet) {
        let lista = exerciciosOrdenados
        for i in offsets { context.delete(lista[i]) }
    }
}
